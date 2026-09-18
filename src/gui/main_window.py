"""Main application window for the Liver Digital Twin.
Patient/case state and output-path management are handled by CaseManager.
Medical-image visualization is handled by VolumeViewer.
Segmentation computation is handled outside the GUI by SegmentationWorker.
"""

from pathlib import Path
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QStatusBar, QTabWidget, QWidget

from src.core.case_manager import CaseManager
from src.gui.viewer.slice_viewer import VolumeViewer
from src.io.dicom_io import load_dicom
from src.io.nifti_io import load_nifti
from src.segmentation_module.segmentation_runner import SegmentationWorker
from src.gui.tabs import data_tab


class MainWindow(QMainWindow):
    # Main graphical interface for the Liver Digital Twin.

    def __init__(self):
        """Initialize the application window and its components."""
        super().__init__()

        # Application components
        self.case_manager = CaseManager()

        # References are kept while segmentation is running.
        self.segmentation_thread = None
        self.segmentation_worker = None

        self._configure_window()
        self._build_ui()

    # Window construction
    # =====================================================================

    def _configure_window(self):
        """Configure the main application window."""
        self.setWindowTitle("Liver Digital Twin")
        self.resize(1200, 800)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready - Load medical imaging data.")

    def _build_ui(self):
        """Build the main application interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left side: tabs
        self.tabs = QTabWidget()
        self.data_tab = data_tab.DataTab()
        self.segmentation_tab = data_tab.SegmentationTab()

        self.tabs.addTab(self.data_tab, "Data")
        self.tabs.addTab(self.segmentation_tab, "Segmentation")

        # Connect Data tab controls
        self.data_tab.load_nifti_button.clicked.connect(self.load_nifti_file)
        self.data_tab.load_dicom_button.clicked.connect(self.load_dicom_folder)
        self.data_tab.slice_slider.valueChanged.connect(self.change_slice)
        self.data_tab.ww_control.valueChanged.connect(self.viewer_window_width_changed)
        self.data_tab.wl_control.valueChanged.connect(self.viewer_window_level_changed)

        # Connect Segmentation tab control
        self.segmentation_tab.segment_button.clicked.connect(self.start_liver_segmentation)

        # Right side: existing viewer
        self.viewer = VolumeViewer()

        main_layout.addWidget(self.tabs, 1)
        main_layout.addWidget(self.viewer, 4)

    # NIfTI loading
    # =====================================================================

    def load_nifti_file(self):
        """Open a file dialog and load a NIfTI CT volume."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select NIfTI Volume", "", "NIfTI Files (*.nii *.nii.gz)")

        # The user pressed Cancel.
        if not file_path:
            return

        try:
            self.statusBar().showMessage("Loading NIfTI volume...")
            volume = load_nifti(file_path)

            # CaseManager now owns the case information.
            self.case_manager.set_nifti_case(file_path, volume)
            self._display_loaded_volume(volume)

            source_path = Path(file_path)
            self.data_tab.file_label.setText(f"NIfTI\n{source_path.name}")
            self.statusBar().showMessage("NIfTI volume loaded successfully.")

            self._load_existing_segmentation_if_available()

        except Exception as error:
            QMessageBox.critical(self, "Unable to Load NIfTI", str(error))
            self.statusBar().showMessage("Failed to load NIfTI volume.")

    # DICOM loading
    # =====================================================================

    def load_dicom_folder(self):
        """Open a folder-selection dialog and load a DICOM series."""
        folder_path = QFileDialog.getExistingDirectory(self, "Select DICOM Folder", "")

        # The user pressed Cancel.
        if not folder_path:
            return

        try:
            self.statusBar().showMessage("Loading DICOM series...")
            volume = load_dicom(folder_path)

            # CaseManager stores the DICOM source and resulting volume.
            self.case_manager.set_dicom_case(folder_path, volume)
            self._display_loaded_volume(volume)

            source_path = Path(folder_path)
            self.data_tab.file_label.setText(f"DICOM\n{source_path.name}")
            self.statusBar().showMessage("DICOM series loaded successfully.")

            self._load_existing_segmentation_if_available()

        except Exception as error:
            QMessageBox.critical(self, "Unable to Load DICOM", str(error))
            self.statusBar().showMessage("Failed to load DICOM series.")

    # Volume display
    # =====================================================================

    def _display_loaded_volume(self, volume):
        """
        Display a newly loaded CT and configure its viewer controls.

        Parameters
        ----------
        volume : MedicalVolume
            CT volume loaded from NIfTI or DICOM.
        """
        self.viewer.set_volume(volume)
        self._configure_controls_for_volume()

    def _configure_controls_for_volume(self):
        """Configure slice and viewing controls for the current CT."""
        ct_volume = self.case_manager.ct_volume

        if ct_volume is None:
            return

        number_of_slices = ct_volume.voxel_data.shape[0]
        middle_slice = number_of_slices // 2

        self.data_tab.slice_slider.setRange(0, number_of_slices - 1)
        self.data_tab.slice_slider.setValue(middle_slice)
        self.data_tab.slice_slider.setEnabled(True)
        self.data_tab.ww_control.setEnabled(True)
        self.data_tab.wl_control.setEnabled(True)
        self.segmentation_tab.segment_button.setEnabled(True)

        self._update_slice_label(middle_slice)

    # Existing segmentation
    # =====================================================================

    def _load_existing_segmentation_if_available(self):
        try:
            mask_volume = self.case_manager.get_existing_liver_mask()

        except Exception as error:
            self.statusBar().showMessage(f"Existing segmentation could not be loaded: {error}")
            self.segmentation_tab.segment_button.setText("Segment Liver")
            return

        if mask_volume is None:
            self.segmentation_tab.segment_button.setText("Segment Liver")
            return

        self.viewer.set_mask(mask_volume)
        self.segmentation_tab.segment_button.setText("Re-run Liver Segmentation")
        self.statusBar().showMessage("Existing liver segmentation loaded.")

    # Slice navigation
    # =====================================================================

    def change_slice(self, slice_index):
        self.viewer.set_slice(slice_index)
        self._update_slice_label(slice_index)

    def _update_slice_label(self, slice_index):
        """Update the displayed current/total slice number."""
        ct_volume = self.case_manager.ct_volume

        if ct_volume is None:
            self.data_tab.slice_label.setText("Slice: -")
            return

        number_of_slices = ct_volume.voxel_data.shape[0]
        self.data_tab.slice_label.setText(f"Slice: {slice_index + 1} / {number_of_slices}")

    # CT Window Width / Window Level
    # =====================================================================

    def viewer_window_width_changed(self, value):
        """Apply the selected Window Width to the viewer."""
        self.viewer.set_window_width(value)

    def viewer_window_level_changed(self, value):
        """Apply the selected Window Level to the viewer."""
        self.viewer.set_window_level(value)

    # Liver segmentation
    # =====================================================================

    def start_liver_segmentation(self):
        """
        Start or re-run liver segmentation for the current CT.

        CaseManager prepares the appropriate NIfTI input.
        SegmentationWorker runs TotalSegmentator outside the GUI thread.
        """
        if self.case_manager.ct_volume is None:
            return

        existing_mask_path = self.case_manager.get_liver_mask_path()

        # If a mask is already loaded, clicking again means the user
        # is explicitly asking to regenerate the segmentation.
        if existing_mask_path.exists() and self.case_manager.liver_mask is not None:
            answer = QMessageBox.question(
                self,
                "Re-run Liver Segmentation",
                "A liver segmentation already exists for this medical volume.\n\nDo you want to run TotalSegmentator again?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if answer != QMessageBox.StandardButton.Yes:
                return

        try:
            self.statusBar().showMessage("Preparing segmentation input...")
            input_path = self.case_manager.prepare_segmentation_input()
            output_directory = self.case_manager.get_results_directory()

        except Exception as error:
            QMessageBox.critical(self, "Segmentation Preparation Failed", str(error))
            return

        self._set_processing_state(True)
        self.statusBar().showMessage("Running liver segmentation...")

        self.segmentation_thread = QThread()
        self.segmentation_worker = SegmentationWorker(input_path=input_path, output_directory=output_directory)

        # Run the worker outside the main GUI thread.
        self.segmentation_worker.moveToThread(self.segmentation_thread)

        self.segmentation_thread.started.connect(self.segmentation_worker.run)
        self.segmentation_worker.finished.connect(self.segmentation_finished)
        self.segmentation_worker.failed.connect(self.segmentation_failed)
        self.segmentation_worker.finished.connect(self.segmentation_thread.quit)
        self.segmentation_worker.failed.connect(self.segmentation_thread.quit)
        self.segmentation_thread.finished.connect(self.segmentation_worker.deleteLater)
        self.segmentation_thread.finished.connect(self.segmentation_thread.deleteLater)

        self.segmentation_thread.start()

    def segmentation_finished(self, mask_path):
        """Load and display a newly generated liver segmentation."""
        try:
            generated_mask_path = Path(mask_path)
            expected_mask_path = self.case_manager.get_liver_mask_path()

            # Store the result using the case-specific filename.
            if generated_mask_path.resolve() != expected_mask_path.resolve():
                if expected_mask_path.exists():
                    expected_mask_path.unlink()

                generated_mask_path.replace(expected_mask_path)

            mask_volume = load_nifti(str(expected_mask_path))

            # CaseManager validates that the mask belongs to the active CT.
            self.case_manager.set_liver_mask(mask_volume)
            self.viewer.set_mask(mask_volume)

            self.segmentation_tab.segment_button.setText("Re-run Liver Segmentation")
            self.statusBar().showMessage("Liver segmentation completed.")

        except Exception as error:
            QMessageBox.critical(self, "Unable to Display Segmentation", str(error))
            self.statusBar().showMessage("Segmentation completed but the mask could not be displayed.")

        finally:
            self._set_processing_state(False)

    def segmentation_failed(self, error_message):
        """Display an error when liver segmentation fails."""
        QMessageBox.critical(self, "Liver Segmentation Failed", error_message)
        self.statusBar().showMessage("Liver segmentation failed.")
        self._set_processing_state(False)

    def _set_processing_state(self, processing):
        """Enable or disable controls while segmentation is running."""
        has_volume = self.case_manager.ct_volume is not None

        self.data_tab.load_nifti_button.setEnabled(not processing)
        self.data_tab.load_dicom_button.setEnabled(not processing)
        self.data_tab.slice_slider.setEnabled(has_volume and not processing)
        self.data_tab.ww_control.setEnabled(has_volume and not processing)
        self.data_tab.wl_control.setEnabled(has_volume and not processing)
        self.segmentation_tab.segment_button.setEnabled(has_volume and not processing)