"""
2D medical-volume viewer for the Liver Digital Twin.

The viewer displays axial CT slices from a MedicalVolume object and can
optionally overlay a binary segmentation mask.

Current functionality
---------------------
- Axial CT visualization
- Slice navigation
- Window Width (WW)
- Window Level (WL)
- Segmentation-mask overlay

The viewer intentionally does not load files itself. It receives already
loaded MedicalVolume objects from the main application.
"""

import numpy as np

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6.QtWidgets import QVBoxLayout, QWidget


class VolumeViewer(QWidget):
    """
    Qt widget used to display axial slices of a medical volume.

    Parameters
    ----------
    parent : QWidget, optional
        Parent Qt widget.
    """

    def __init__(self, parent=None):
        """Initialize an empty CT viewer."""

        super().__init__(parent)

        self.ct_volume = None
        self.mask_volume = None

        self.current_slice = 0

        # Default abdominal soft-tissue window.
        self.window_width = 300
        self.window_level = 50

        self._build_ui()

    def _build_ui(self):
        """Create the embedded Matplotlib canvas."""

        self.figure = Figure()

        self.canvas = FigureCanvasQTAgg(
            self.figure
        )

        self.axes = self.figure.add_subplot(111)
        self.axes.axis("off")

        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)

    def set_volume(self, volume):
        """
        Display a new CT MedicalVolume.

        Parameters
        ----------
        volume : MedicalVolume
            CT volume that should become the active image.
        """

        self.ct_volume = volume

        # A new patient must never inherit the previous patient's mask.
        self.mask_volume = None

        num_slices = (
            self.ct_volume.voxel_data.shape[0]
        )

        # Start near the center of the scan rather than slice zero.
        self.current_slice = (
            num_slices // 2
        )

        self.update_display()

    def set_mask(self, mask_volume):
        """
        Add a segmentation mask to the displayed CT.

        Parameters
        ----------
        mask_volume : MedicalVolume
            Binary segmentation volume aligned with the CT.
        """

        self.mask_volume = mask_volume

        self.update_display()

    def clear_mask(self):
        """Remove the currently displayed segmentation overlay."""

        self.mask_volume = None

        self.update_display()

    def set_slice(self, slice_index):
        """
        Display a selected axial slice.

        Parameters
        ----------
        slice_index : int
            Zero-based axial slice index.
        """

        if self.ct_volume is None:
            return

        number_of_slices = (
            self.ct_volume.voxel_data.shape[0]
        )

        self.current_slice = max(
            0,
            min(
                int(slice_index),
                number_of_slices - 1,
            ),
        )

        self.update_display()

    def set_window_width(self, width):
        """
        Update CT Window Width.

        Parameters
        ----------
        width : int or float
            Width of the displayed Hounsfield-unit range.
        """

        # WW cannot mathematically be zero or negative.
        self.window_width = max(
            float(width),
            1.0,
        )

        self.update_display()

    def set_window_level(self, level):
        """
        Update CT Window Level.

        Parameters
        ----------
        level : int or float
            Center of the displayed Hounsfield-unit range.
        """

        self.window_level = float(level)

        self.update_display()

    def update_display(self):
        """
        Redraw the current CT slice and optional segmentation overlay.

        Window Width and Window Level are converted to lower and upper
        display limits using:

            lower = WL - WW / 2
            upper = WL + WW / 2
        """

        if self.ct_volume is None:
            return

        ct_data = (
            self.ct_volume.voxel_data
        )

        ct_slice = ct_data[
            self.current_slice,
            :,
            :,
        ]

        lower_limit = (
            self.window_level
            - self.window_width / 2
        )

        upper_limit = (
            self.window_level
            + self.window_width / 2
        )

        self.axes.clear()

        self.axes.imshow(
            ct_slice,
            cmap="gray",
            vmin=lower_limit,
            vmax=upper_limit,
            origin="lower",
        )

        # Draw the segmentation only if a mask has been loaded.
        if self.mask_volume is not None:

            mask_data = (
                self.mask_volume.voxel_data
            )

            # Protect against mismatched image dimensions.
            if mask_data.shape == ct_data.shape:

                mask_slice = mask_data[
                    self.current_slice,
                    :,
                    :,
                ]

                # Hide background voxels so the underlying CT stays visible.
                masked_liver = np.ma.masked_where(
                    mask_slice == 0,
                    mask_slice,
                )

                self.axes.imshow(
                    masked_liver,
                    cmap="Reds",
                    alpha=0.4,
                    vmin=0,
                    vmax=1,
                    origin="lower",
                )

        self.axes.set_title(
            f"Axial Slice {self.current_slice + 1}"
        )

        self.axes.axis("off")

        self.canvas.draw_idle()