""" Main application window for the Liver Digital Twin.
Patient/case state and output-path management are handled by CaseManager.
Medical-image visualization is handled by VolumeViewer.
Segmentation computation is handled outside the GUI by SegmentationWorker.
"""

from pathlib import Path
from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import ( QFileDialog, QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QSlider, QSpinBox, QStatusBar,QVBoxLayout, QWidget)
from src.core.case_manager import CaseManager
from src.gui.volume_viewer import VolumeViewer
from src.io.dicom_io import load_dicom
from src.io.nifti_io import load_nifti
from src.segmentation_module.segmentation_runner import SegmentationWorker


class MainWindow(QMainWindow):
    # Main graphical interface for the Liver Digital Twin.
    def __init__(self):
        """Initialize the application window and its components."""
        super().__init__()
    # Application components
        # Stores information about the currently loaded medical case.
        self.case_manager = CaseManager()
        # References are kept while segmentation is running.
        self.segmentation_thread = None
        self.segmentation_worker = None

        self._configure_window()
        self._build_ui()

    # Window construction
    def _configure_window(self):
        """Configure the main application window."""
        self.setWindowTitle("Liver Digital Twin")
        self.resize(1200, 800)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready - Load medical imaging data.")

    def _build_ui(self):
        """
        Build the main application layout.

        The window currently consists of:
        - a control panel on the left;
        - the medical-volume viewer on the right.
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        control_panel = self._create_control_panel()
        self.viewer = VolumeViewer()

        # The viewer receives more horizontal space than the controls.
        main_layout.addWidget(control_panel, 1)
        main_layout.addWidget(self.viewer, 4)

    def _create_control_panel(self):
        #Create the controls used to interact with the current case.
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Patient data
        # ==============================================================

        data_group = QGroupBox("Patient Data")
        data_layout = QVBoxLayout(data_group)
        self.load_nifti_button = QPushButton("Load NIfTI")
        self.load_nifti_button.clicked.connect(self.load_nifti_file)
        self.load_dicom_button = QPushButton("Load DICOM Folder")
        self.load_dicom_button.clicked.connect(self.load_dicom_folder)
        self.file_label = QLabel("No volume loaded")
        self.file_label.setWordWrap(True)

        data_layout.addWidget(self.load_nifti_button)
        data_layout.addWidget(self.load_dicom_button)
        data_layout.addWidget(self.file_label)

        # Slice navigation
        # ==============================================================
        slice_group = QGroupBox("Slice Navigation")
        slice_layout = QVBoxLayout(slice_group)

        self.slice_label = QLabel("Slice: -")
        self.slice_slider = QSlider(Qt.Orientation.Horizontal)
        self.slice_slider.setEnabled(False)
        self.slice_slider.valueChanged.connect(self.change_slice)

        slice_layout.addWidget(self.slice_label)
        slice_layout.addWidget(self.slice_slider)

        # ==============================================================
        # CT windowing
        # ==============================================================
        window_group = QGroupBox("CT Windowing")
        window_layout = QVBoxLayout(window_group)

        # Window Width
        window_layout.addWidget(QLabel("Window Width (WW)"))
        self.ww_control = QSpinBox()
        self.ww_control.setRange(1, 4000)
        self.ww_control.setValue(300)
        self.ww_control.setEnabled(False)
        self.ww_control.valueChanged.connect(self.viewer_window_width_changed)
        window_layout.addWidget(self.ww_control)

        # Window Level
        window_layout.addWidget(QLabel("Window Level (WL)"))
        self.wl_control = QSpinBox()
        self.wl_control.setRange(-2000, 2000)
        self.wl_control.setValue(50)
        self.wl_control.setEnabled(False)
        self.wl_control.valueChanged.connect(self.viewer_window_level_changed)
        window_layout.addWidget(self.wl_control)

        # Liver segmentation
        # ==============================================================
        segmentation_group = QGroupBox("Liver Segmentation")
        segmentation_layout = QVBoxLayout(segmentation_group)
        self.segment_button = QPushButton("Segment Liver")
        self.segment_button.setEnabled(False)
        self.segment_button.clicked.connect(self.start_liver_segmentation)

        segmentation_layout.addWidget(self.segment_button)

        # Assemble control panel
        # ==============================================================
        layout.addWidget(data_group)
        layout.addWidget(slice_group)
        layout.addWidget(window_group)
        layout.addWidget(segmentation_group)

        # Keeps the controls near the top of the panel.
        layout.addStretch()

        return panel
    