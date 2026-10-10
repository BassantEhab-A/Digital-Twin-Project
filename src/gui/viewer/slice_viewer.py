"""
Orthogonal 2D slice pane for the Liver Digital Twin.

Each pane = [PaneHeader on top] + [Matplotlib canvas below].

The pane can overlay SEVERAL masks at once (liver, vessels, tumors, Couinaud
segments). All visible masks are composited into ONE RGBA image per redraw,
which is much faster than one imshow per structure.
"""
from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from src.core.stuctures import STRUCTURE_BY_KEY
from src.gui.viewer.pane_header import PaneHeader

PLANE_AXIAL = "axial"
PLANE_CORONAL = "coronal"
PLANE_SAGITTAL = "sagittal"

MASK_ALPHA = 0.5

# volume axis (in a (Z, Y, X) array) that is fixed for each plane
_VOLUME_AXIS_FOR_PLANE = {PLANE_AXIAL: 0, PLANE_CORONAL: 1, PLANE_SAGITTAL: 2}
# index into crosshair (X, Y, Z)
_CROSSHAIR_INDEX_FOR_PLANE = {PLANE_AXIAL: 2, PLANE_CORONAL: 1, PLANE_SAGITTAL: 0}
# (row_axis, col_axis) of the displayed 2D slice, as indices into (X, Y, Z)
_ROW_COL_XYZ = {
    PLANE_AXIAL: (1, 0),     # rows = Y, cols = X
    PLANE_CORONAL: (2, 0),   # rows = Z, cols = X
    PLANE_SAGITTAL: (2, 1),  # rows = Z, cols = Y
}
_ORIENTATION_LETTERS = {
    PLANE_AXIAL: "R A L P",
    PLANE_CORONAL: "R S L I",
    PLANE_SAGITTAL: "A S P I",
}

# structure key -> RGBA float tuple, computed once
_RGBA = {k: to_rgba(s.color, MASK_ALPHA) for k, s in STRUCTURE_BY_KEY.items()}


class SliceView(QWidget):
    slice_changed = Signal(str, int)
    voxel_clicked = Signal(str, int, int)

    def __init__(self, plane: str, parent=None):
        super().__init__(parent)
        self.plane = plane
        self.ct_volume = None
        self.masks = {}            # structure key -> MedicalVolume
        self.visible = set()       # keys currently shown
        self.current_index = 0
        self.window_width = 300.0
        self.window_level = 50.0
        self.crosshair = (0, 0, 0)  # (X, Y, Z)
        self.overlay_text = ""
        self._dragging = False
        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = PaneHeader(self.plane, letters=_ORIENTATION_LETTERS[self.plane])
        self.header.slider_moved.connect(self._on_slider_moved)
        layout.addWidget(self.header)

        self.figure = Figure(facecolor="black")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setMinimumSize(50, 50)
        self.axes = self.figure.add_subplot(111)
        self.axes.axis("off")
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)

        self.canvas.mpl_connect("button_press_event", self._on_mpl_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_mpl_motion)
        self.canvas.mpl_connect("button_release_event", self._on_mpl_release)
        self.canvas.mpl_connect("scroll_event", self._on_mpl_scroll)

        self.setFocusPolicy(Qt.StrongFocus)
        layout.addWidget(self.canvas, 1)

    # ----------------------------------------------------------- helpers
    def _axis_length(self) -> int:
        axis = _VOLUME_AXIS_FOR_PLANE[self.plane]
        return int(self.ct_volume.voxel_data.shape[axis])

    def _aspect(self) -> float:
        """Physical (row_mm / col_mm) so voxels are drawn with true shape."""
        spacing = self.ct_volume.spacing_xyz          # (x, y, z)
        row_axis, col_axis = _ROW_COL_XYZ[self.plane]
        row_mm, col_mm = spacing[row_axis], spacing[col_axis]
        if col_mm <= 0 or row_mm <= 0:
            return 1.0
        return float(row_mm / col_mm)

    def _origin(self) -> str:
        # Axial: anterior (small Y) at the top. Coronal/sagittal: superior up.
        return "upper" if self.plane == PLANE_AXIAL else "lower"

    # ----------------------------------------------------------- public API
    def set_volume(self, volume) -> None:
        self.ct_volume = volume
        self.masks = {}
        self.visible = set()
        if volume is not None:
            total = self._axis_length()
            self.current_index = int(np.clip(self.current_index, 0, total - 1))
            self.header.set_range(0, total - 1)
            self.header.set_value(self.current_index)
            self._update_position_label()
        self.update_display()

    def set_masks(self, masks: dict, visible=None) -> None:
        """Replace all overlays. `visible` = keys to show (default: all)."""
        self.masks = dict(masks)
        self.visible = set(self.masks if visible is None else visible)
        self.update_display()

    def set_mask_visible(self, key: str, visible: bool) -> None:
        if visible:
            self.visible.add(key)
        else:
            self.visible.discard(key)
        self.update_display()

    def clear_masks(self) -> None:
        self.masks = {}
        self.visible = set()
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
        self.overlay_text = text or ""
        self.update_display()

    # ------------------------------------------------------- matplotlib events
    def _on_mpl_press(self, event) -> None:
        if self.ct_volume is None or event.inaxes is not self.axes:
            return
        if event.button != 1 or event.xdata is None or event.ydata is None:
            return
        self._dragging = True
        self._emit_click(event)

    def _on_mpl_motion(self, event) -> None:
        if not self._dragging or self.ct_volume is None:
            return
        if event.inaxes is not self.axes or event.xdata is None:
            return
        self._emit_click(event)

    def _on_mpl_release(self, _event) -> None:
        self._dragging = False

    def _emit_click(self, event) -> None:
        self.voxel_clicked.emit(
            self.plane, int(round(event.xdata)), int(round(event.ydata))
        )

    def _on_mpl_scroll(self, event) -> None:
        if self.ct_volume is None:
            return
        step = 1 if event.button == "up" else -1
        new_index = int(np.clip(self.current_index + step, 0, self._axis_length() - 1))
        if new_index != self.current_index:
            self.slice_changed.emit(self.plane, new_index)

    def _on_slider_moved(self, value: int) -> None:
        if self.ct_volume is None:
            return
        self.slice_changed.emit(self.plane, value)

    # ------------------------------------------------------------- drawing
    def _slice_from_volume(self, volume: np.ndarray) -> np.ndarray:
        axis = _VOLUME_AXIS_FOR_PLANE[self.plane]
        idx = int(np.clip(self.current_index, 0, volume.shape[axis] - 1))
        if axis == 0:
            return volume[idx, :, :]
        if axis == 1:
            return volume[:, idx, :]
        return volume[:, :, idx]

    def _index_from_crosshair(self) -> int:
        return int(self.crosshair[_CROSSHAIR_INDEX_FOR_PLANE[self.plane]])

    def _update_position_label(self) -> None:
        if self.ct_volume is None:
            self.header.set_position_label("0.0mm")
            return
        axis_zyx = _VOLUME_AXIS_FOR_PLANE[self.plane]
        mm = self.current_index * float(self.ct_volume.spacing_zyx[axis_zyx])
        self.header.set_position_label(f"{mm:.1f}mm")

    def _compose_overlay(self, ct_shape2d, ct_shape3d):
        """Blend every visible mask into one RGBA image (or None if empty)."""
        keys = [k for k in self.visible if k in self.masks]
        # Low layer first, so tumors/vessels end up on top of liver/segments.
        keys.sort(key=lambda k: STRUCTURE_BY_KEY[k].layer)

        overlay = np.zeros(ct_shape2d + (4,), dtype=np.float32)
        drawn = False
        for key in keys:
            data = self.masks[key].voxel_data
            if data.shape != ct_shape3d:
                continue
            mask2d = self._slice_from_volume(data) > 0
            if mask2d.any():
                overlay[mask2d] = _RGBA[key]
                drawn = True
        return overlay if drawn else None

    def update_display(self) -> None:
        if self.ct_volume is None:
            return
        ct_data = self.ct_volume.voxel_data
        ct_slice = self._slice_from_volume(ct_data)
        lower = self.window_level - self.window_width / 2.0
        upper = self.window_level + self.window_width / 2.0
        aspect = self._aspect()
        origin = self._origin()

        self.axes.clear()
        self.axes.imshow(
            ct_slice, cmap="gray", vmin=lower, vmax=upper,
            origin=origin, interpolation="nearest", aspect=aspect,
        )

        overlay = self._compose_overlay(ct_slice.shape, ct_data.shape)
        if overlay is not None:
            self.axes.imshow(
                overlay, origin=origin, interpolation="nearest", aspect=aspect,
            )

        self._draw_crosshair()

        if self.overlay_text:
            self.axes.text(
                0.02, 0.02, self.overlay_text, transform=self.axes.transAxes,
                fontsize=8, color="white", ha="left", va="bottom",
                bbox=dict(facecolor="black", alpha=0.5, edgecolor="none", pad=2),
            )

        # Lock the view to the image so the crosshair lines can't autoscale it.
        h, w = ct_slice.shape
        self.axes.set_xlim(-0.5, w - 0.5)
        if origin == "upper":
            self.axes.set_ylim(h - 0.5, -0.5)
        else:
            self.axes.set_ylim(-0.5, h - 0.5)
        self.axes.axis("off")
        self.canvas.draw_idle()

    def _draw_crosshair(self) -> None:
        x, y, z = self.crosshair
        row_axis, col_axis = _ROW_COL_XYZ[self.plane]
        xyz = (x, y, z)
        row, col = xyz[row_axis], xyz[col_axis]
        kw = dict(color="lime", linewidth=0.8, alpha=0.9)
        self.axes.axhline(row, **kw)
        self.axes.axvline(col, **kw)