"""
Data tab used in the Liver Digital Twin GUI.
 
This module contains the UI layout for loading data and viewing controls.
Application logic remains in MainWindow.
(The Segmentation tab now lives in segmentation_tab.py.)
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

        # Slice Navigation : I removed this part since we substitued it with the paneheader
        # =========================================================

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
        layout.addWidget(window_group)
        layout.addStretch()


