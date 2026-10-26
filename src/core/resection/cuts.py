"""Cut definitions: each one answers "which liver voxels are removed?".

A cut never touches the GUI or the original masks. Three families:

  * PlaneCut   : geometric plane (axis-aligned, or through 3 picked points)
  * SegmentCut : follows Couinaud segment boundaries
  * suggest_*  : given a tumor + margin zone, propose the cut automatically

Convention: for a plane, `normal` points toward the side that is KEPT.
World axes are LPS (+X left, +Y posterior, +Z superior).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from src.core.medical_volume import MedicalVolume

# Orientation name -> index of the world axis that is the plane's normal.
_ORIENTATION_AXIS = {"sagittal": 0, "coronal": 1, "axial": 2}


class Cut(ABC):
    """Base class: turns a liver mask into the mask of removed voxels."""

    description: str = ""

    @abstractmethod
    def removed_mask(self, liver: MedicalVolume) -> np.ndarray:
        """Boolean (Z, Y, X) array, True where liver tissue is removed."""


class PlaneCut(Cut):
    """Remove the liver on the negative side of a plane."""

    def __init__(self, origin, normal, description: str = "Planar cut"):
        normal = np.asarray(normal, dtype=float)
        length = np.linalg.norm(normal)
        if length == 0:
            raise ValueError("Plane normal cannot be the zero vector.")
        self.origin = np.asarray(origin, dtype=float)
        self.normal = normal / length
        self.description = description

    def removed_mask(self, liver: MedicalVolume) -> np.ndarray:
        idx, points = liver.mask_world_points()
        outside = ((points - self.origin) @ self.normal) < 0
        removed = np.zeros(liver.shape, dtype=bool)
        removed[tuple(a[outside] for a in idx)] = True
        return removed

    # ------------------------------------------------------- constructors
    @classmethod
    def axis_aligned(cls, liver: MedicalVolume, orientation: str,
                     position_pct: float, keep_positive: bool = True) -> "PlaneCut":
        """Plane perpendicular to a world axis, placed along the liver's extent.

        orientation  : 'axial' (normal Z), 'coronal' (normal Y), 'sagittal' (normal X)
        position_pct : 0 = one end of the liver, 100 = the other end
        """
        if orientation not in _ORIENTATION_AXIS:
            raise ValueError(f"Unknown orientation: {orientation!r}")
        axis = _ORIENTATION_AXIS[orientation]
        _, points = liver.mask_world_points()
        if len(points) == 0:
            raise ValueError("The liver mask is empty.")

        low, high = points[:, axis].min(), points[:, axis].max()
        origin = points.mean(axis=0)
        origin[axis] = low + (high - low) * (position_pct / 100.0)

        normal = np.zeros(3)
        normal[axis] = 1.0 if keep_positive else -1.0
        return cls(origin, normal,
                   f"Planar cut ({orientation}, {position_pct:.0f}%)")

    @classmethod
    def from_points(cls, p1, p2, p3, keep_positive: bool = True) -> "PlaneCut":
        """Manual cut: the plane through three picked points (mm)."""
        p1, p2, p3 = (np.asarray(p, dtype=float) for p in (p1, p2, p3))
        normal = np.cross(p2 - p1, p3 - p1)
        if np.linalg.norm(normal) < 1e-6:
            raise ValueError("The three points are on one line - they do not define a plane.")
        if not keep_positive:
            normal = -normal
        return cls(p1, normal, "Manual cut (3 points)")


class SegmentCut(Cut):
    """Remove whole Couinaud segments (cuts follow the segment boundaries)."""

    def __init__(self, segment_masks: dict, keys, description: str = ""):
        keys = list(keys)
        missing = [k for k in keys if k not in segment_masks]
        if not keys:
            raise ValueError("Select at least one segment to remove.")
        if missing:
            raise ValueError("Segment mask(s) not available: " + ", ".join(missing))
        self.segment_masks = segment_masks
        self.keys = keys
        self.description = description or "Anatomical cut (" + ", ".join(
            k.replace("liver_segment_", "S") for k in keys) + ")"

    def removed_mask(self, liver: MedicalVolume) -> np.ndarray:
        removed = np.zeros(liver.shape, dtype=bool)
        for key in self.keys:
            removed |= self.segment_masks[key].voxel_data > 0
        return removed & (liver.voxel_data > 0)


# --------------------------------------------------------------- suggestions
def _fibonacci_directions(n: int) -> np.ndarray:
    """~uniform unit vectors on the whole sphere."""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(theta) * np.sin(phi),
                     np.sin(theta) * np.sin(phi),
                     np.cos(phi)], axis=1)


def suggest_plane_cut(liver: MedicalVolume, required: np.ndarray,
                      n_directions: int = 400, chunk: int = 32) -> PlaneCut:
    """Best single plane that removes every `required` voxel (tumor + margin).

    For each candidate normal n (pointing to the KEPT side), the tightest
    plane that still removes the whole required zone sits just beyond the
    required voxel with the largest projection on n. The candidate that
    removes the least liver (largest remnant) wins.
    """
    required = np.asarray(required) > 0
    if not required.any():
        raise ValueError("No tumor found - nothing to plan a cut around.")

    _, liver_pts = liver.mask_world_points()
    _, req_pts = liver.mask_world_points(required)
    # The search only needs a representative sample of the liver.
    liver_pts = liver_pts[:: max(1, len(liver_pts) // 200_000)].astype(np.float32)
    req_pts = req_pts.astype(np.float32)

    directions = _fibonacci_directions(n_directions).astype(np.float32)
    best_count, best_dir, best_limit = None, None, None
    for start in range(0, len(directions), chunk):
        block = directions[start:start + chunk]
        limits = (req_pts @ block.T).max(axis=0)              # tightest offset per direction
        counts = ((liver_pts @ block.T) <= limits).sum(axis=0)  # liver removed per direction
        k = int(np.argmin(counts))
        if best_count is None or counts[k] < best_count:
            best_count, best_dir, best_limit = int(counts[k]), block[k], float(limits[k])

    normal = best_dir.astype(float)
    # Half a voxel beyond the last required voxel centre, so that voxel is removed.
    offset = best_limit + 0.5 * min(liver.spacing)
    return PlaneCut(normal * offset, normal, "Suggested plane (tumor + margin)")


def suggest_segment_cut(segment_masks: dict, required: np.ndarray) -> SegmentCut:
    """Every Couinaud segment that the tumor + margin zone touches."""
    required = np.asarray(required) > 0
    if not required.any():
        raise ValueError("No tumor found - nothing to plan a cut around.")
    touched = [k for k, m in sorted(segment_masks.items())
               if k.startswith("liver_segment_") and (required & (m.voxel_data > 0)).any()]
    if not touched:
        raise ValueError("The tumor does not overlap any Couinaud segment.")
    return SegmentCut(segment_masks, touched, "Suggested segments (tumor + margin)")
