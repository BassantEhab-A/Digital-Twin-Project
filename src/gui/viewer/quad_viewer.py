"""
2x2 quad layout: Axial | Sagittal over Coronal | 3D.

Synchronizes the crosshair across the three 2D panes and pushes
volume/mask updates to all four panes.
"""

from __future__ import annotations

import numpy as np

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QWidget

from src.gui.viewer.slice_viewer import (
    SliceView,
    PLANE_AXIAL,
    PLANE_CORONAL,
    PLANE_SAGITTAL,
)
from src.gui.viewer.viewer_3d import VolumeViewer3D


class QuadViewer(QWidget):
    """
    Top-left     : Axial
    Top-right    : Sagittal
    Bottom-left  : Coronal
    Bottom-right : 3D
    """

    crosshair_changed = Signal(int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.ct_volume = None
        self.mask_volume = None
        self.crosshair = (0, 0, 0)

        self.window_width = 300.0
        self.window_level = 50.0

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.axial_view = SliceView(PLANE_AXIAL)
        self.sagittal_view = SliceView(PLANE_SAGITTAL)
        self.coronal_view = SliceView(PLANE_CORONAL)
        self.view_3d = VolumeViewer3D()

        for view in (self.axial_view, self.sagittal_view, self.coronal_view):
            view.slice_changed.connect(self._on_slice_changed)
            view.voxel_clicked.connect(self._on_voxel_clicked)

        layout = QGridLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        layout.addWidget(self.axial_view,    0, 0)
        layout.addWidget(self.sagittal_view, 0, 1)
        layout.addWidget(self.coronal_view,  1, 0)
        layout.addWidget(self.view_3d,       1, 1)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

    # ---------------------------------------------------------- public API
    def set_volume(self, volume) -> None:
        self.ct_volume = volume
        self.mask_volume = None

        z, y, x = volume.voxel_data.shape
        self.crosshair = (x // 2, y // 2, z // 2)

        for view in (self.axial_view, self.sagittal_view, self.coronal_view):
            view.set_window(self.window_width, self.window_level)
            view.set_volume(volume)
            view.set_crosshair(*self.crosshair)

        self.view_3d.set_volume(volume)

    def set_mask(self, mask_volume) -> None:
        self.mask_volume = mask_volume
        for view in (self.axial_view, self.sagittal_view, self.coronal_view):
            view.set_mask(mask_volume)
        self.view_3d.set_mask(mask_volume)

    def clear_mask(self) -> None:
        self.mask_volume = None
        for view in (self.axial_view, self.sagittal_view, self.coronal_view):
            view.clear_mask()
        self.view_3d.clear_mask()

    def set_window_width(self, width: float) -> None:
        self.window_width = max(float(width), 1.0)
        self._push_window()

    def set_window_level(self, level: float) -> None:
        self.window_level = float(level)
        self._push_window()

    def set_slice(self, slice_index: int) -> None:
        """Backward-compatible entry point (axial Z slice)."""
        if self.ct_volume is None:
            return
        z = int(np.clip(slice_index, 0, self.ct_volume.voxel_data.shape[0] - 1))
        x, y, _ = self.crosshair
        self._set_crosshair(x, y, z)

    def set_overlay_text(self, text: str) -> None:
        """Forward study-description overlay to all 2D panes."""
        for view in (self.axial_view, self.sagittal_view, self.coronal_view):
            view.set_overlay_text(text)

    # ------------------------------------------------------------- private
    def _push_window(self) -> None:
        for view in (self.axial_view, self.sagittal_view, self.coronal_view):
            view.set_window(self.window_width, self.window_level)

    def _set_crosshair(self, x: int, y: int, z: int) -> None:
        if self.ct_volume is None:
            return
        shape = self.ct_volume.voxel_data.shape
        x = int(np.clip(x, 0, shape[2] - 1))
        y = int(np.clip(y, 0, shape[1] - 1))
        z = int(np.clip(z, 0, shape[0] - 1))

        self.crosshair = (x, y, z)

        for view in (self.axial_view, self.sagittal_view, self.coronal_view):
            view.set_crosshair(x, y, z)

        self.crosshair_changed.emit(x, y, z)

    # --------------------------------------------------------------- slots
    def _on_slice_changed(self, plane: str, new_index: int) -> None:
        if self.ct_volume is None:
            return
        x, y, z = self.crosshair

        if plane == PLANE_AXIAL:
            z = new_index
        elif plane == PLANE_CORONAL:
            y = new_index
        else:  # sagittal
            x = new_index

        self._set_crosshair(x, y, z)

    def _on_voxel_clicked(self, plane: str, u: int, v: int) -> None:
        if self.ct_volume is None:
            return
        x, y, z = self.crosshair

        if plane == PLANE_AXIAL:        # u = X, v = Y
            x, y = u, v
        elif plane == PLANE_CORONAL:    # u = X, v = Z
            x, z = u, v
        else:                           # sagittal: u = Y, v = Z
            y, z = u, v

        self._set_crosshair(x, y, z)