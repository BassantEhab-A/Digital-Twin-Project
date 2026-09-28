"""
3D viewer pane (PyVista/VTK) that displays ONLY the liver surface.

"""
from __future__ import annotations

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor

from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.gui.viewer.pane_header import PaneHeader


# ---------------------------------------------------------------- tuning
LIVER_COLOR = "#d98c7a"        # warm salmon
LIVER_OPACITY = 1.0
BACKGROUND = "#e8ebf0"         # very light lavender-gray

BOX_COLOR = "magenta"
BOX_LINE_WIDTH = 1.5
BOX_PADDING = 15.0             # mm of padding around the liver bounds

LABEL_COLOR = "magenta"
LABEL_FONT_SIZE = 18
LABEL_OFFSET = 30.0            # mm from the box face to the label


class VolumeViewer3D(QWidget):
    """GPU-accelerated 3D view showing only the liver surface."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.ct_volume = None
        self.mask_volume = None

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = PaneHeader("three_d", letters="")
        layout.addWidget(self.header)

        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter.interactor, 1)

        self.plotter.set_background(BACKGROUND)
        self.plotter.add_axes()

    # ---------------------------------------------------------- public API
    def set_volume(self, volume) -> None:
        """Kept for API compatibility — the CT itself is not rendered."""
        self.ct_volume = volume
        self.update_display()

    def set_mask(self, mask_volume) -> None:
        self.mask_volume = mask_volume
        self.update_display()

    def clear_mask(self) -> None:
        self.mask_volume = None
        self.update_display()

    # ------------------------------------------------------------- render
    def update_display(self) -> None:
        # Need both CT (for spacing) and mask (for the surface).
        if self.ct_volume is None or self.mask_volume is None:
            self.plotter.clear()
            self.plotter.add_axes()
            self.plotter.set_background(BACKGROUND)
            return

        if self.mask_volume.voxel_data.shape != self.ct_volume.voxel_data.shape:
            print("[3D] Mask shape does not match CT — not rendering.")
            self.plotter.clear()
            self.plotter.add_axes()
            return

        self.plotter.clear()
        self.plotter.add_axes()
        self.plotter.set_background(BACKGROUND)

        # ---- spacing: SimpleITK gives (z, y, x); VTK wants (x, y, z) ----
        spacing_zxy = tuple(float(s) for s in self.ct_volume.spacing)
        spacing_xyz = spacing_zxy[::-1]

        # ---- mask grid ------------------------------------------------
        mask = self.mask_volume.voxel_data                # (Z, Y, X)
        mask_xyz = np.ascontiguousarray(
            np.transpose(mask, (2, 1, 0))                 # -> (X, Y, Z)
        )

        mgrid = pv.ImageData()
        mgrid.dimensions = mask_xyz.shape
        mgrid.spacing = spacing_xyz
        mgrid.point_data["mask"] = mask_xyz.ravel(order="F")
        mgrid.set_active_scalars("mask")

        # ---- extract the liver surface --------------------------------
        liver = mgrid.contour(
            [0.5], scalars="mask", method="marching_cubes"
        )

        if liver.n_points == 0:
            print("[3D] Liver mesh is empty — mask may be all zeros.")
            return

        # Smooth the stair-step voxel edges (PyVista 0.45+ signature).
        liver = liver.smooth(
            n_iter=20,
            relaxation_factor=0.1,
            convergence=0.0,
            edge_angle=15,
            feature_angle=45,
            boundary_smoothing=True,
            feature_smoothing=False,
            inplace=False,
        )

        self.plotter.add_mesh(
            liver,
            color=LIVER_COLOR,
            opacity=LIVER_OPACITY,
            smooth_shading=True,
            specular=0.15,
            diffuse=0.9,
            ambient=0.35,
            name="liver",
        )

        # ---- orientation bounding box (magenta wireframe) -------------
        b = liver.bounds
        pad = BOX_PADDING
        bounds = (
            b[0] - pad, b[1] + pad,
            b[2] - pad, b[3] + pad,
            b[4] - pad, b[5] + pad,
        )
        box = pv.Box(bounds=bounds)
        self.plotter.add_mesh(
            box,
            style="wireframe",
            color=BOX_COLOR,
            line_width=BOX_LINE_WIDTH,
            name="orientation_box",
        )

        # ---- A/P/L/R/S/I labels on the box edges ----------------------
        xmin, xmax, ymin, ymax, zmin, zmax = bounds
        cx = (xmin + xmax) / 2
        cy = (ymin + ymax) / 2
        cz = (zmin + zmax) / 2
        off = LABEL_OFFSET

        label_positions = [
            ((cx, ymax + off, cz), "A"),   # Anterior
            ((cx, ymin - off, cz), "P"),   # Posterior
            ((xmax + off, cy, cz), "L"),   # Left
            ((xmin - off, cy, cz), "R"),   # Right
            ((cx, cy, zmax + off), "S"),   # Superior
            ((cx, cy, zmin - off), "I"),   # Inferior
        ]

        for position, text in label_positions:
            self.plotter.add_point_labels(
                [position],
                [text],
                font_size=LABEL_FONT_SIZE,
                text_color=LABEL_COLOR,
                shape=None,
                show_points=False,
                always_visible=True,
                name=f"label_{text}",
            )

        # ---- camera ---------------------------------------------------
        self.plotter.reset_camera()
        self.plotter.view_isometric()
        self.plotter.camera.zoom(1.3)