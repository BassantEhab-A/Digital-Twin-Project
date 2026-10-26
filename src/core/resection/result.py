"""Data object returned by a resection simulation."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ResectionResult:
    """Outcome of one simulated resection. Masks are full-size (Z, Y, X) booleans."""
    original_volume_ml: float
    remnant_volume_ml: float
    removed_volume_ml: float
    remnant_percentage: float          # remnant / whole liver
    flr_percentage: float              # remnant / (liver - tumor): the clinical FLR
    retained_mask: np.ndarray
    removed_mask: np.ndarray
    is_safe: bool
    safety_message: str
    cut_description: str = ""
    tumor_volume_ml: float = 0.0
    margin_required_mm: float = 0.0
    margin_achieved_mm: float | None = None   # None when there is no tumor
    tumor_covered: bool = True         # no tumor voxel is left in the remnant
    margin_satisfied: bool = True      # whole tumor + margin zone is removed
    required_mask: np.ndarray | None = None   # tumor dilated by the margin
    warnings: tuple = ()
    effective_flr_percentage: float | None = None   # FLR minus tissue that lost inflow/outflow
    vascular: object | None = None                  # VascularImpact, when vessels were analysed
