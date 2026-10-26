"""Distance-based helpers: tumor margins. Pure numpy/scipy, no GUI."""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage


def crop_slices(mask: np.ndarray, pad_zyx) -> tuple | None:
    """Slices of the bounding box of `mask` grown by `pad_zyx` voxels (clipped)."""
    if not mask.any():
        return None
    slices = []
    for axis, pad in enumerate(pad_zyx):
        other = tuple(a for a in range(3) if a != axis)
        nz = np.flatnonzero(mask.any(axis=other))
        lo = max(int(nz[0]) - int(pad), 0)
        hi = min(int(nz[-1]) + int(pad) + 1, mask.shape[axis])
        slices.append(slice(lo, hi))
    return tuple(slices)


def expand_mask_mm(mask: np.ndarray, spacing_xyz, margin_mm: float) -> np.ndarray:
    """Grow a binary mask by `margin_mm` (true Euclidean distance, anisotropic voxels).

    The distance transform is computed only inside the mask's bounding box
    (plus the margin), so it stays cheap on a full CT.
    """
    mask = np.asarray(mask) > 0
    if margin_mm <= 0 or not mask.any():
        return mask.copy()

    spacing_zyx = tuple(float(s) for s in spacing_xyz)[::-1]
    pad = [math.ceil(margin_mm / s) + 1 for s in spacing_zyx]
    box = crop_slices(mask, pad)

    distance = ndimage.distance_transform_edt(~mask[box], sampling=spacing_zyx)
    grown = np.zeros_like(mask)
    grown[box] = distance <= margin_mm
    return grown


def min_distance_mm(source: np.ndarray, target: np.ndarray, spacing_xyz) -> float | None:
    """Smallest distance (mm) from any `source` voxel to any `target` voxel.

    Returns None if either mask is empty.
    """
    source = np.asarray(source) > 0
    target = np.asarray(target) > 0
    if not source.any() or not target.any():
        return None

    spacing_zyx = tuple(float(s) for s in spacing_xyz)[::-1]
    box = crop_slices(source | target, (1, 1, 1))
    distance = ndimage.distance_transform_edt(~source[box], sampling=spacing_zyx)
    return float(distance[target[box]].min())
