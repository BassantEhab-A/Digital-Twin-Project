"""A 3D medical image (CT or mask) with its patient-space geometry."""
from __future__ import annotations

import numpy as np

_IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)


class MedicalVolume:
    """A 3D image plus the geometry that places it in patient space (mm).

      * voxel_data : numpy array indexed (Z, Y, X)   [SimpleITK array order]
      * spacing    : (X, Y, Z) in mm                 [SimpleITK GetSpacing order]
      * origin     : (X, Y, Z) in mm
      * direction  : flattened 3x3 matrix (row-major, SimpleITK order)
      * metadata   : optional dict (e.g. DICOM tags)

    World coordinates are LPS (+X = left, +Y = posterior, +Z = superior).
    Use the helpers below instead of indexing `spacing` by hand.
    """

    def __init__(self, voxel_data, spacing, origin, direction=None, metadata=None):
        self.voxel_data = voxel_data
        self.spacing = tuple(float(s) for s in spacing)
        self.origin = tuple(float(o) for o in origin)
        self.direction = tuple(float(d) for d in (direction or _IDENTITY))
        self.metadata = metadata or {}

    # ------------------------------------------------------------ geometry
    @property
    def shape(self) -> tuple:
        return self.voxel_data.shape

    @property
    def spacing_xyz(self) -> tuple:
        return self.spacing

    @property
    def spacing_zyx(self) -> tuple:
        """Spacing in the same order as voxel_data axes."""
        return self.spacing[::-1]

    @property
    def voxel_volume_mm3(self) -> float:
        return float(np.prod(self.spacing))

    def _direction_matrix(self) -> np.ndarray:
        return np.asarray(self.direction, dtype=float).reshape(3, 3)

    def voxel_to_world(self, ijk_xyz) -> np.ndarray:
        """Voxel indices (x, y, z) -> patient coordinates in mm.

        Accepts one index (3,) or many (N, 3); returns the same shape.
        """
        idx = np.asarray(ijk_xyz, dtype=float)
        scaled = idx * np.asarray(self.spacing)
        return scaled @ self._direction_matrix().T + np.asarray(self.origin)

    def world_to_voxel(self, xyz_mm) -> np.ndarray:
        """Patient coordinates in mm -> fractional voxel indices (x, y, z)."""
        pts = np.asarray(xyz_mm, dtype=float) - np.asarray(self.origin)
        inverse = np.linalg.inv(self._direction_matrix())
        return (pts @ inverse.T) / np.asarray(self.spacing)

    # -------------------------------------------------------------- masks
    def volume_ml(self, mask=None) -> float:
        """Volume in millilitres of `mask` (default: voxels > 0 of this volume)."""
        selected = self.voxel_data > 0 if mask is None else mask
        return float(np.count_nonzero(selected)) * self.voxel_volume_mm3 / 1000.0

    def like(self, voxel_data) -> "MedicalVolume":
        """A new volume with the same geometry but different voxel data."""
        return MedicalVolume(
            voxel_data, self.spacing, self.origin, self.direction, self.metadata
        )

    def mask_world_points(self, mask=None) -> tuple:
        """(indices, points) of the non-zero voxels.

        indices : tuple of three arrays (z, y, x), usable to index voxel_data
        points  : (N, 3) patient coordinates in mm
        Only the selected voxels are converted, never the full grid.
        """
        selected = self.voxel_data > 0 if mask is None else mask
        z, y, x = np.nonzero(selected)
        points = self.voxel_to_world(np.stack([x, y, z], axis=1))
        return (z, y, x), points
