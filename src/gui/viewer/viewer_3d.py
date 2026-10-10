"""
3D viewer pane (PyVista/VTK) that displays ONLY the liver surface.

"""
from __future__ import annotations
import traceback   

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from src.core.stuctures import STRUCTURE_BY_KEY
from src.gui.viewer.pane_header import PaneHeader


LIVER_COLOR = "#d98c7a"        
BACKGROUND = "#e8ebf0"  
LIVER_CONTEXT_OPACITY = 0.30   # liver opacity while other structures are shown        
BOX_COLOR = "magenta"
BOX_LINE_WIDTH = 1.5
BOX_PADDING = 15.0             # mm of padding around the liver bounds
LABEL_COLOR = "magenta"
LABEL_FONT_SIZE = 18
LABEL_OFFSET = 30.0            # mm from the box face to the label

idle_message= "Run Segmentation to see the 3D structures."

def _bbox(binary: np.ndarray):
    #Inclusive voxel bounding box (z0, z1, y0, y1, x0, x1) or None if empty.
    if not np.any(binary):
        return None
    zs=np.flatnonzero(binary.any(axis=(1,2)))
    ys=np.flatnonzero(binary.any(axis=(0,2)))
    xs=np.flatnonzero(binary.any(axis=(0,1)))
    return (zs[0], zs[-1], ys[0], ys[-1], xs[0], xs[-1])
def mask_bounds_mm(mask_zyx,spacing_xyz, origin_xyz):
    """(xmin, xmax, ymin, ymax, zmin, zmax) of a mask in mm, or None if empty."""
    box = _bbox(np.asarray(mask_zyx)>0)
    if box is None:
        return None
    z0, z1, y0, y1, x0, x1 = box
    sx, sy, sz = (float(s) for s in spacing_xyz)
    ox, oy, oz = (float(o) for o in origin_xyz)
    return (ox+ x0*sx, ox+ (x1+1)*sx,
            oy+ y0*sy, oy+ (y1+1)*sy,
            oz+ z0*sz, oz+ (z1+1)*sz)
def build_mask_mesh(mask_zyx, spacing_xyz, origin_xyz, keep_largest=False):
    """Marching cubes on a (Z, Y, X) mask -> smoothed surface in patient mm.
       spacing_xyz / origin_xyz are in (x, y, z) order (SimpleITK order).
        Returns an empty PolyData if the mask is empty.
         """
    binary = np.asarray(mask_zyx)>0
    box = _bbox(binary)
    if box is None:
        return pv.PolyData()  # empty mesh

    z0, z1, y0, y1, x0, x1 = box
    crop = binary[z0:z1+1, y0:y1+1, x0:x1+1].astype(np.uint8)
    crop = np.pad(crop,1)  
    mask_xyz = np.ascontiguousarray(np.transpose(crop, (2, 1, 0)))
    sx, sy, sz = (float(s) for s in spacing_xyz)    
    ox, oy, oz = (float(o) for o in origin_xyz)

    grid = pv.ImageData(
        dimensions=mask_xyz.shape,
        spacing=(sx, sy, sz),
         # crop offset, minus 1 voxel for the padding
        origin=(ox + (x0-1)*sx, oy + (y0-1)*sy, oz + (z0-1)*sz),)
    grid.point_data["mask"] = mask_xyz.ravel(order="F")
    mesh = grid.contour([0.5], scalars="mask", method="marching_cubes")
    if mesh.n_points == 0:
        return mesh  # empty mesh
    if keep_largest:
        mesh = mesh.extract_largest()  
    try:
        mesh = mesh.smooth_taubin(n_iter=30, pass_band=0.08)
    except Exception as err: 
     print(f"[3D] Smoothing skipped: {err}")
    mesh.compute_normals(inplace=True, auto_orient_normals=False)
    return mesh

class VolumeViewer3D(QWidget):
    """GPU-accelerated 3D view showing only the liver surface."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ct_volume = None
        self.masks = {}            # key -> MedicalVolume
        self.visible = set()
        self._meshes = {}          # key -> PolyData (cache)
        self._scene_ready = False
        self._dirty = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = PaneHeader("three_d", letters="")
        layout.addWidget(self.header)

        self.status = QLabel(idle_message)
        self.status.setWordWrap
        self.status.setStyleSheet(
            "background:#f4f4f4; color:#333; padding:4px; font-size:11px;"
        )
        layout.addWidget(self.status)

        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter.interactor, 1)

        self.plotter.set_background(BACKGROUND)
       # self.plotter.add_axes()   --- not added

    def set_volume(self, volume) -> None:
        """Kept for API compatibility — the CT itself is not rendered."""
        self.ct_volume = volume
        self._reset_masks()
        self._set_status(idle_message)
        self._request_render()

    def set_masks(self, masks: dict, visible_keys) -> None:
        self.masks = dict(masks)
        self.visible = set(visible_keys) & set(self.masks)
        self._meshes.clear()
        self._request_render()

    def set_mask_visible(self, key: str, visible: bool) -> None:
        if key not in self.masks:
            return
        if visible:
            self.visible.add(key)
        else:
            self.visible.discard(key)
        if self._scene_ready and self.isVisible():
            self._safely(self._apply_visibility)      # incremental: no camera jump
        else:
            self._request_render() 

    def clear_mask(self) -> None:
        self._reset_masks()
        self._set_status(idle_message)
        self._request_render()
    def shutdown(self) -> None:
        try:
            self.plotter.close()
        except Exception as err:
            print(f"[3D] Plotter close failed: {err}")
 
    def closeEvent(self, event) -> None:
        self.shutdown()
        super().closeEvent(event)
 
    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._dirty:
            self._request_render()

    ##--------------------------------------------
    def _reset_masks(self) -> None:
        self.masks = {}
        self.visible = set()
        self._meshes.clear()
 
    def _set_status(self, text: str) -> None:
        self.status.setText(text)
        self.status.setVisible(bool(text))
 
    def _request_render(self) -> None:
        if not self.isVisible():
            self._dirty = True            # rendered later from showEvent
            return
        self._dirty = False
        QTimer.singleShot(0, self.update_display)
 
    def _safely(self, func) -> None:
        try:
            func()
        except Exception as err:
            traceback.print_exc()
            self._set_status(f"3D rendering failed: {type(err).__name__}: {err}")
 
    def _get_mesh(self, key: str):
        """Build a structure's mesh on first use, then reuse it."""
        if key not in self._meshes:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                self._meshes[key] = build_mask_mesh(
                    self.masks[key].voxel_data,
                    self.ct_volume.spacing_xyz,
                    self.ct_volume.origin,
                    keep_largest=STRUCTURE_BY_KEY[key].keep_largest,
                )
            finally:
                QApplication.restoreOverrideCursor()
        return self._meshes[key]
    ## RENDER
    # ------------------------------------------------------------- render
    def _clear_scene(self) -> None:
        self.plotter.clear()
        self.plotter.set_background(BACKGROUND)
        self.plotter.add_axes()
        self._scene_ready = False
        self.plotter.render()
    def update_display(self) -> None:
        """Full rebuild: new volume or new set of masks."""
        self._safely(self._rebuild_scene)
 
    def _rebuild_scene(self) -> None:
        self._clear_scene()
        if self.ct_volume is None or not self.masks:
            return
 
        spacing, origin = self.ct_volume.spacing_xyz, self.ct_volume.origin
 
        # Stable bounds from ALL masks (cheap, no meshing) so the box and the
        # camera don't move when structures are toggled.
        all_bounds = [
            b for b in (mask_bounds_mm(m.voxel_data, spacing, origin)
                        for m in self.masks.values()) if b is not None
        ]
        empty_labels = [
            STRUCTURE_BY_KEY[k].label for k, m in self.masks.items()
            if not m.voxel_data.any()
        ]
        if not all_bounds:
            self._set_status("3D: all masks are empty (nothing was found).")
            return
 
        xmin = min(b[0] for b in all_bounds) - BOX_PADDING
        xmax = max(b[1] for b in all_bounds) + BOX_PADDING
        ymin = min(b[2] for b in all_bounds) - BOX_PADDING
        ymax = max(b[3] for b in all_bounds) + BOX_PADDING
        zmin = min(b[4] for b in all_bounds) - BOX_PADDING
        zmax = max(b[5] for b in all_bounds) + BOX_PADDING
 
        self.plotter.add_mesh(
            pv.Box(bounds=(xmin, xmax, ymin, ymax, zmin, zmax)),
            style="wireframe", color=BOX_COLOR, line_width=BOX_LINE_WIDTH,
            name="orientation_box", reset_camera=False, render=False,
        )
        self._add_orientation_labels(xmin, xmax, ymin, ymax, zmin, zmax)
        self._apply_visibility(render=False)
 
        # Camera: from the front (anterior = -Y), a little left and above.
        center = np.array([(xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2])
        dist = 2.2 * max(xmax - xmin, ymax - ymin, zmax - zmin)
        direction = np.array([0.35, -1.0, 0.30])
        direction /= np.linalg.norm(direction)
        self.plotter.camera_position = [
            tuple(center + direction * dist), tuple(center), (0.0, 0.0, 1.0),
        ]
        self.plotter.reset_camera_clipping_range()
        self.plotter.render()
 
        self._scene_ready = True
        self._set_status(
            "Not found: " + ", ".join(empty_labels) if empty_labels else ""
        )
    def _add_orientation_labels(self, xmin, xmax, ymin, ymax, zmin, zmax) -> None:
        cx, cy, cz = (xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2
        off = LABEL_OFFSET
        # Image coordinates are LPS: +X = Left, +Y = Posterior, +Z = Superior
        labels = [
            ((xmax + off, cy, cz), "L"), ((xmin - off, cy, cz), "R"),
            ((cx, ymax + off, cz), "P"), ((cx, ymin - off, cz), "A"),
            ((cx, cy, zmax + off), "S"), ((cx, cy, zmin - off), "I"),
        ]
        try:  # cosmetic - never let labels break the structures
            self.plotter.add_point_labels(
                pv.PolyData(np.array([p for p, _ in labels], dtype=float)),
                [t for _, t in labels],
                font_size=LABEL_FONT_SIZE, text_color=LABEL_COLOR,
                shape=None, show_points=False, always_visible=True,
                name="orientation_labels", render=False,
            )
        except Exception as err:
            print(f"[3D] Orientation labels skipped: {err}")
 
    def _apply_visibility(self, render: bool = True) -> None:
        """Add/remove actors to match `self.visible`. Does not touch the camera."""
        shown = [k for k in self.visible if self.masks[k].voxel_data.any()]
        others_shown = any(k != "liver" for k in shown)
 
        for key in self.masks:
            if key in shown:
                mesh = self._get_mesh(key)
                if mesh.n_points == 0:
                    continue
                opacity = LIVER_CONTEXT_OPACITY if (key == "liver" and others_shown) else 1.0
                self.plotter.add_mesh(
                    mesh, color=STRUCTURE_BY_KEY[key].color, opacity=opacity,
                    smooth_shading=True, specular=0.15, diffuse=0.9, ambient=0.35,
                    name=key, reset_camera=False, render=False,
                )
            else:
                try:
                    self.plotter.remove_actor(key, render=False)
                except Exception:
                    pass          # actor was never added
        if render:
            self.plotter.render()