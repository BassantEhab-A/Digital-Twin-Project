"""Resection simulation: apply a Cut, measure what is left, check safety.

Independent of the GUI. Inputs are MedicalVolumes (binary masks); the
original masks are never modified.
"""
from __future__ import annotations

import numpy as np

from src.core.medical_volume import MedicalVolume
from src.core.resection.cuts import Cut
from src.core.resection.margin import expand_mask_mm, min_distance_mm
from src.core.resection.result import ResectionResult
from src.core.resection.vessels import VesselTree


class ResectionEngine:
    # Minimum future liver remnant (FLR). Commonly ~20 % for a healthy liver,
    # ~30 % after chemotherapy, ~40 % for cirrhosis. Pass `threshold_percent`
    # to `simulate` to change it.
    SAFETY_THRESHOLD_PERCENT = 30.0

    @staticmethod
    def evaluate_safety(flr_percentage: float, threshold: float) -> tuple:
        if flr_percentage >= threshold:
            return True, (f"SAFE: future liver remnant is {flr_percentage:.1f} %, "
                          f"above the {threshold:.0f} % threshold.")
        return False, (f"WARNING: future liver remnant is only {flr_percentage:.1f} %, "
                       f"below the {threshold:.0f} % threshold. "
                       "High risk of post-hepatectomy liver failure.")

    @classmethod
    def simulate(cls, liver: MedicalVolume, cut: Cut, tumor: MedicalVolume | None = None,
                 margin_mm: float = 0.0, threshold_percent: float | None = None,
                 vessel_tree: VesselTree | None = None, min_vessel_diameter_mm: float = 2.0
                 ) -> ResectionResult:
        """Apply `cut` to `liver` and report volumes, margin, vascular impact and safety.

        With a `vessel_tree`, the tissue that loses its portal inflow or venous
        outflow is subtracted from the remnant (effective FLR).
        """
        threshold = cls.SAFETY_THRESHOLD_PERCENT if threshold_percent is None else threshold_percent
        liver_mask = liver.voxel_data > 0
        if not liver_mask.any():
            raise ValueError("The liver mask is empty.")

        removed = cut.removed_mask(liver) & liver_mask
        retained = liver_mask & ~removed

        tumor_mask = np.zeros_like(liver_mask)
        if tumor is not None:
            tumor_mask = (tumor.voxel_data > 0) & liver_mask
        has_tumor = bool(tumor_mask.any())

        required = None
        if has_tumor:
            required = expand_mask_mm(tumor_mask, liver.spacing, margin_mm) & liver_mask

        # Volumes. The clinical FLR excludes the tumor from the denominator.
        original_ml = liver.volume_ml(liver_mask)
        remnant_ml = liver.volume_ml(retained)
        removed_ml = liver.volume_ml(removed)
        functional = liver_mask & ~tumor_mask
        functional_ml = liver.volume_ml(functional)
        flr_ml = liver.volume_ml(retained & ~tumor_mask)
        remnant_pct = remnant_ml / original_ml * 100.0
        flr_pct = flr_ml / functional_ml * 100.0 if functional_ml > 0 else 0.0

        # Oncologic checks.
        warnings = []
        tumor_covered = margin_ok = True
        achieved = None
        if has_tumor:
            tumor_covered = not (tumor_mask & retained).any()
            margin_ok = not (required & retained).any()
            achieved = min_distance_mm(tumor_mask, retained, liver.spacing)
            if not tumor_covered:
                warnings.append("Part of the tumor is left in the remnant.")
            elif not margin_ok:
                warnings.append(f"The {margin_mm:g} mm margin is not fully respected"
                                + (f" (achieved {achieved:.1f} mm)." if achieved is not None else "."))

        # Vascular impact: tissue cut off from inflow/outflow is not functional remnant.
        vascular, effective_flr = None, None
        if vessel_tree is not None:
            vascular = vessel_tree.impact(liver, removed, retained, min_vessel_diameter_mm)
            lost_ml = liver.volume_ml(vascular.devascularized_mask & ~tumor_mask)
            effective_flr = max(flr_ml - lost_ml, 0.0) / functional_ml * 100.0 if functional_ml > 0 else 0.0
            if vascular.severed_portal or vascular.severed_hepatic:
                warnings.append(f"Severed branches (>= {min_vessel_diameter_mm:g} mm): "
                                f"{vascular.severed_portal} portal, {vascular.severed_hepatic} hepatic.")
            if vascular.devascularized_ml > 0:
                warnings.append(f"{vascular.ischemic_ml:.0f} mL of remnant loses portal inflow, "
                                f"{vascular.congested_ml:.0f} mL loses venous outflow.")
            warnings.extend(vascular.warnings)

        is_safe, message = cls.evaluate_safety(
            flr_pct if effective_flr is None else effective_flr, threshold)
        return ResectionResult(
            original_volume_ml=original_ml, remnant_volume_ml=remnant_ml,
            removed_volume_ml=removed_ml, remnant_percentage=remnant_pct,
            flr_percentage=flr_pct, retained_mask=retained, removed_mask=removed,
            is_safe=is_safe, safety_message=message,
            cut_description=cut.description,
            tumor_volume_ml=liver.volume_ml(tumor_mask),
            margin_required_mm=float(margin_mm), margin_achieved_mm=achieved,
            tumor_covered=tumor_covered, margin_satisfied=margin_ok,
            required_mask=required, warnings=tuple(warnings),
            effective_flr_percentage=effective_flr, vascular=vascular,
        )
