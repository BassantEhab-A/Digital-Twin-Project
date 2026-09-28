"""
Orthogonal 2D slice pane for the Liver Digital Twin.

Each pane = [PaneHeader on top] + [Matplotlib canvas below].

The pane knows how to:
  * extract a 2D slice from a (Z, Y, X) volume,
  * overlay a mask,
  * draw crosshair lines from a shared (X, Y, Z) crosshair,
  * emit slice changes and click events to the parent viewer,
  * render a small study-description overlay in the corner.
"""

from __future__ import annotations

import numpy as np

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.gui.viewer.pane_header import PaneHeader


PLANE_AXIAL = "axial"
PLANE_CORONAL = "coronal"
PLANE_SAGITTAL = "sagittal"


_VOLUME_AXIS_FOR_PLANE = {
    PLANE_AXIAL: 0,      # Z
    PLANE_CORONAL: 1,    # Y
    PLANE_SAGITTAL: 2,   # X
}

_CROSSHAIR_INDEX_FOR_PLANE = {
    PLANE_AXIAL: 2,      # Z
    PLANE_CORONAL: 1,    # Y
    PLANE_SAGITTAL: 0,   # X
}

_ORIENTATION_LETTERS = {
    PLANE_AXIAL:    "R   A   L   P",
    PLANE_CORONAL:  "R   S   L   I",
    PLANE_SAGITTAL: "A   S   P   I",
}


class SliceView(QWidget):
    """A single orthogonal 2D view with its own header bar."""

    slice_changed = Signal(str, int)
    voxel_clicked = Signal(str, int, int)

    def __init__(self, plane: str, parent=None):
        super().__init__(parent)

        self.plane = plane

        self.ct_volume = None
        self.mask_volume = None

        self.current_index = 0
        self.window_width = 300.0
        self.window_level = 50.0

        # Shared crosshair in voxel coords (X, Y, Z).
        self.crosshair = (0, 0, 0)

        # Small text drawn in the bottom-left corner (e.g. study description).
        self.overlay_text = ""

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = PaneHeader(
            self.plane, letters=_ORIENTATION_LETTERS[self.plane]
        )
        self.header.slider_moved.connect(self._on_slider_moved)
        layout.addWidget(self.header)

        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.axes = self.figure.add_subplot(111)
        self.axes.axis("off")
        self.figure.patch.set_alpha(0.0)
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)

        self.setFocusPolicy(Qt.StrongFocus)
        layout.addWidget(self.canvas, 1)

    # ----------------------------------------------------------- public API
    def set_volume(self, volume, mask_volume=None) -> None:
        self.ct_volume = volume
        self.mask_volume = mask_volume

        if volume is not None:
            axis = _VOLUME_AXIS_FOR_PLANE[self.plane]
            total = volume.voxel_data.shape[axis]
            self.header.set_range(0, total - 1)
            self.header.set_value(self.current_index)

        self.update_display()

    def set_mask(self, mask_volume) -> None:
        self.mask_volume = mask_volume
        self.update_display()

    def clear_mask(self) -> None:
        self.mask_volume = None
        self.update_display()

    def set_window(self, width: float, level: float) -> None:
        self.window_width = max(float(width), 1.0)
        self.window_level = float(level)
        self.update_display()

    def set_crosshair(self, x: int, y: int, z: int) -> None:
        self.crosshair = (int(x), int(y), int(z))
        self.current_index = self._index_from_crosshair()
        self.header.set_value(self.current_index)
        self._update_position_label()
        self.update_display()

    def set_overlay_text(self, text: str) -> None:
        """Small annotation shown in the bottom-left corner."""
        self.overlay_text = text or ""
        self.update_display()

    # ---------------------------------------------------------- event hooks
    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            return
        step = 1 if delta > 0 else -1
        new_index = self.current_index + step

        axis = _VOLUME_AXIS_FOR_PLANE[self.plane]
        total = self.ct_volume.voxel_data.shape[axis]
        new_index = max(0, min(total - 1, new_index))

        self.slice_changed.emit(self.plane, new_index)
        event.accept()

    def mousePressEvent(self, event) -> None:
        if self.ct_volume is None:
            return

        widget_pos = event.position().toPoint()
        canvas_pos = self.canvas.mapFrom(self, widget_pos)

        x_disp = canvas_pos.x()
        y_disp = self.canvas.height() - canvas_pos.y()

        inv = self.axes.transData.inverted()
        x_data, y_data = inv.transform((x_disp, y_disp))

        u = int(round(x_data))
        v = int(round(y_data))

        self.voxel_clicked.emit(self.plane, u, v)

    # --------------------------------------------------------------- slots
    def _on_slider_moved(self, value: int) -> None:
        if self.ct_volume is None:
            return
        self.slice_changed.emit(self.plane, value)

    # ------------------------------------------------------------- drawing
    def _slice_from_volume(self, volume) -> np.ndarray:
        axis = _VOLUME_AXIS_FOR_PLANE[self.plane]
        idx = self.current_index
        if axis == 0:
            return volume[idx, :, :]
        if axis == 1:
            return volume[:, idx, :]
        return volume[:, :, idx]

    def _index_from_crosshair(self) -> int:
        idx = _CROSSHAIR_INDEX_FOR_PLANE[self.plane]
        return int(self.crosshair[idx])

    def _update_position_label(self) -> None:
        if self.ct_volume is None:
            self.header.set_position_label("0.0mm")
            return
        axis = _VOLUME_AXIS_FOR_PLANE[self.plane]
        idx = self.current_index
        spacing = self.ct_volume.spacing  # (z, y, x)
        mm = idx * float(spacing[axis])
        self.header.set_position_label(f"{mm:.1f}mm")

    def update_display(self) -> None:
        if self.ct_volume is None:
            return

        ct_data = self.ct_volume.voxel_data
        ct_slice = self._slice_from_volume(ct_data)

        lower = self.window_level - self.window_width / 2.0
        upper = self.window_level + self.window_width / 2.0

        self.axes.clear()

        self.axes.imshow(
            ct_slice,
            cmap="gray",
            vmin=lower,
            vmax=upper,
            origin="lower",
            interpolation="nearest",
        )

        if self.mask_volume is not None:
            mask_data = self.mask_volume.voxel_data
            if mask_data.shape == ct_data.shape:
                mask_slice = self._slice_from_volume(mask_data)
                masked = np.ma.masked_where(mask_slice == 0, mask_slice)
                self.axes.imshow(
                    masked,
                    cmap="Oranges",
                    alpha=0.45,
                    vmin=0,
                    vmax=1,
                    origin="lower",
                    interpolation="nearest",
                )

        self._draw_crosshair()

        # Small study-description overlay (bottom-left corner).
        if self.overlay_text:
            self.axes.text(
                0.02, 0.02, self.overlay_text,
                transform=self.axes.transAxes,
                fontsize=8,
                color="white",
                ha="left",
                va="bottom",
                bbox=dict(
                    facecolor="black",
                    alpha=0.5,
                    edgecolor="none",
                    pad=2,
                ),
            )

        self.axes.axis("off")
        self.canvas.draw_idle()

    def _draw_crosshair(self) -> None:
        if self.ct_volume is None:
            return

        x, y, z = self.crosshair
        axis = _VOLUME_AXIS_FOR_PLANE[self.plane]

        if axis == 0:          # axial: rows = Y, cols = X
            row, col = y, x
        elif axis == 1:        # coronal: rows = Z, cols = X
            row, col = z, x
        else:                  # sagittal: rows = Z, cols = Y
            row, col = z, y

        line_kw = dict(color="lime", linewidth=0.8, alpha=0.9)
        self.axes.axhline(row, **line_kw)
        self.axes.axvline(col, **line_kw)