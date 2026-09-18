"""
Tabs used in the Liver Digital Twin GUI.

This module contains the UI layout for the Data and Segmentation tabs.
Application logic remains in MainWindow.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QGroupBox,QPushButton,QLabel,QSlider,QSpinBox)


class DataTab(QWidget):
    """UI controls for loading and viewing medical data."""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # =========================================================
        # Patient Data
        # =========================================================

        patient_group = QGroupBox("Patient Data")
        patient_layout = QVBoxLayout(patient_group)

        self.load_nifti_button = QPushButton("Load NIfTI")
        self.load_dicom_button = QPushButton("Load DICOM Folder")

        self.file_label = QLabel("No volume loaded")
        self.file_label.setWordWrap(True)

        patient_layout.addWidget(self.load_nifti_button)
        patient_layout.addWidget(self.load_dicom_button)
        patient_layout.addWidget(self.file_label)

        # Slice Navigation
        # =========================================================

        slice_group = QGroupBox("Slice Navigation")
        slice_layout = QVBoxLayout(slice_group)

        self.slice_label = QLabel("Slice: -")

        self.slice_slider = QSlider(Qt.Orientation.Horizontal)
        self.slice_slider.setEnabled(False)

        slice_layout.addWidget(self.slice_label)
        slice_layout.addWidget(self.slice_slider)

        # =========================================================
        # CT Windowing
        # =========================================================

        window_group = QGroupBox("CT Windowing")
        window_layout = QVBoxLayout(window_group)

        window_layout.addWidget(QLabel("Window Width (WW)"))

        self.ww_control = QSpinBox()
        self.ww_control.setRange(1, 4000)
        self.ww_control.setValue(300)
        self.ww_control.setEnabled(False)

        window_layout.addWidget(self.ww_control)

        window_layout.addWidget(QLabel("Window Level (WL)"))

        self.wl_control = QSpinBox()
        self.wl_control.setRange(-2000, 2000)
        self.wl_control.setValue(50)
        self.wl_control.setEnabled(False)

        window_layout.addWidget(self.wl_control)

        # =========================================================
        # Final layout
        # =========================================================

        layout.addWidget(patient_group)
        layout.addWidget(slice_group)
        layout.addWidget(window_group)
        layout.addStretch()


class SegmentationTab(QWidget):
    """UI controls for liver segmentation."""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        segmentation_group = QGroupBox("Liver Segmentation")
        segmentation_layout = QVBoxLayout(segmentation_group)

        self.segment_button = QPushButton("Segment Liver")
        self.segment_button.setEnabled(False)

        segmentation_layout.addWidget(self.segment_button)

        layout.addWidget(segmentation_group)
        layout.addStretch()