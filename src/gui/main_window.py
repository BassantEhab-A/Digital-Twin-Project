"""Main application window for the Liver Digital Twin.

Patient/case state and output-path management are handled by CaseManager.

Medical-image visualization is handled by QuadViewer.

Segmentation computation is handled outside the GUI by SegmentationWorker;
WHAT can be segmented is defined in src/core/structures.py.
"""

from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (QFileDialog,QHBoxLayout,QMainWindow,QMessageBox,QStatusBar, QTabWidget,QWidget,)
from src.core.case_manager import CaseManager
# from src.core.structures import (STRUCTURE_BY_KEY, plan_runs, missing_runs, keys_for_groups)
from src.core.stuctures import (STRUCTURE_BY_KEY, plan_runs, missing_runs, keys_for_groups) 
from src.gui.tabs import data_tab, segmentation_tab
from src.gui.viewer.quad_viewer import QuadViewer
from src.io.dicom_io import load_dicom
from src.io.nifti_io import load_nifti
from src.segmentation_module.segmentation_runner import SegmentationWorker


class MainWindow(QMainWindow):
    """Main graphical interface for the Liver Digital Twin."""

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
        self.resize(1400, 900)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready - Load medical imaging data.")

    def _build_ui(self):
        """Build the main application interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # ------------------------------------------------------------
        # Left side: tabs
        # ------------------------------------------------------------
        self.tabs = QTabWidget()
        self.data_tab = data_tab.DataTab()
        self.segmentation_tab = segmentation_tab.SegmentationTab()
        self.tabs.addTab(self.data_tab, "Data")
        self.tabs.addTab(self.segmentation_tab, "Segmentation")

        # ------------------------------------------------------------
        # Right side: 2x2 quad viewer (axial / sagittal / coronal / 3D)
        # ------------------------------------------------------------
        self.viewer = QuadViewer()

        main_layout.addWidget(self.tabs, 0)
        main_layout.addWidget(self.viewer, 1)

        # Connect Data tab controls
        self.data_tab.load_nifti_button.clicked.connect(self.load_nifti_file)
        self.data_tab.load_dicom_button.clicked.connect(self.load_dicom_folder)
        self.data_tab.ww_control.valueChanged.connect(self.viewer_window_width_changed)
        self.data_tab.wl_control.valueChanged.connect(self.viewer_window_level_changed)

        # Connect Segmentation tab controls
        self.segmentation_tab.segment_button.clicked.connect(self.start_segmentation)
        self.segmentation_tab.visibility_changed.connect(self.viewer.set_mask_visible)
        for check in self.segmentation_tab.group_checks.values():
            check.toggled.connect(self._refresh_segment_button)
        self.segmentation_tab.force_check.toggled.connect(self._refresh_segment_button)

    def closeEvent(self, event):
        """Release the VTK render window cleanly.

        Qt only sends closeEvent to the top-level window, so child widgets
        (like the 3D viewer) must be shut down from here.
        """
        self.viewer.shutdown()
        super().closeEvent(event)

    # NIfTI loading
    # =====================================================================
    def load_nifti_file(self):
        """Open a file dialog and load a NIfTI CT volume."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select NIfTI Volume", "", "NIfTI Files (*.nii *.nii.gz)"
        )

        # The user pressed Cancel.
        if not file_path:
            return

        try:
            self.statusBar().showMessage("Loading NIfTI volume...")
            volume = load_nifti(file_path)

            # CaseManager owns the case information.
            self.case_manager.set_nifti_case(file_path, volume)
            self._display_loaded_volume(volume)

            source_path = Path(file_path)
            self.data_tab.file_label.setText(f"NIfTI\n{source_path.name}")
            self.statusBar().showMessage("NIfTI volume loaded successfully.")

            self._refresh_segment_button()

        except Exception as error:
            QMessageBox.critical(self, "Unable to Load NIfTI", str(error))
            self.statusBar().showMessage("Failed to load NIfTI volume.")

    # DICOM loading
    # =====================================================================
    def load_dicom_folder(self):
        """Open a folder-selection dialog and load a DICOM series."""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select DICOM Folder", ""
        )

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

            self._refresh_segment_button()

        except Exception as error:
            QMessageBox.critical(self, "Unable to Load DICOM", str(error))
            self.statusBar().showMessage("Failed to load DICOM series.")

    # Volume display
    # =====================================================================
    def _display_loaded_volume(self, volume):
        """Display a newly loaded CT and configure its viewer controls."""
        self.viewer.set_volume(volume)
        self.segmentation_tab.reset_results()       # masks belonged to the old CT
        self._configure_controls_for_volume()

        # Push study/series description to each 2D pane's corner overlay.
        self.viewer.set_overlay_text(self._build_overlay_text(volume))

    def _build_overlay_text(self, volume):
        """
        Build a short overlay string from a MedicalVolume's DICOM metadata.

        Returns an empty string when no metadata is available (e.g. NIfTI).
        """
        meta = getattr(volume, "metadata", None) or {}
        study = (meta.get("StudyDescription") or "").strip()
        series = (meta.get("SeriesDescription") or "").strip()
        parts = [p for p in (study, series) if p]
        return " ".join(parts)

    def _configure_controls_for_volume(self):
        """Configure slice and viewing controls for the current CT."""
        ct_volume = self.case_manager.ct_volume
        if ct_volume is None:
            return
      
        self.data_tab.ww_control.setEnabled(True)
        self.data_tab.wl_control.setEnabled(True)
        self.segmentation_tab.segment_button.setEnabled(True)


    # Saved segmentations (loaded only when the user asks)
    # =====================================================================
    def _refresh_segment_button(self, *_):
        """Make the button and the info line say what a click will do.

        Nothing is loaded here - only file names on disk are checked.
        """
        tab = self.segmentation_tab
        if self.case_manager.ct_volume is None:
            tab.segment_button.setText("Run Segmentation")
            tab.set_saved_info("")
            return

        try:
            case_dir = self.case_manager.get_results_directory()
            runs = plan_runs(tab.selected_groups())
            pending = missing_runs(runs, case_dir)
            saved = [
                STRUCTURE_BY_KEY[k].label for k in self.case_manager.existing_mask_keys()
            ]
        except Exception as error:
            tab.set_saved_info(f"Could not check saved results: {error}")
            return

        if tab.force_rerun():
            tab.segment_button.setText("Re-run Segmentation")
        elif not pending:
            tab.segment_button.setText("Load Saved Segmentation")
        else:
            tab.segment_button.setText("Run Segmentation")

        if saved:
            tab.set_saved_info(f"Saved results found: {', '.join(saved)}.")
        else:
            tab.set_saved_info("No saved results for this volume yet.")

    def _load_masks_from_disk(self, keys):
        """Load saved masks for `keys` and display them. No model is run."""
        try:
            found = self.case_manager.get_existing_masks(keys)
        except Exception as error:
            QMessageBox.critical(self, "Unable to Load Segmentation", str(error))
            return

        if not found:
            self.statusBar().showMessage("No saved segmentation could be loaded.")
            return

        empty_labels = self._show_masks()
        message = f"Loaded {len(found)} saved structure(s) - nothing was recomputed."
        if empty_labels:
            message += " Nothing found for: " + ", ".join(empty_labels) + "."
        self.statusBar().showMessage(message)

    def _show_masks(self):
        """Push the CaseManager's masks to the viewer and the display checkboxes.

        Returns the labels of structures whose mask is empty ('none found').
        """
        masks = dict(self.case_manager.masks)
        empty = {k for k, m in masks.items() if not m.voxel_data.any()}

        # The tab first (it decides default visibility), then the viewer.
        self.segmentation_tab.set_available(set(masks), empty)
        self.viewer.set_masks(masks, self.segmentation_tab.visible_keys())
        return [STRUCTURE_BY_KEY[k].label for k in sorted(empty)]


    # CT Window Width / Window Level
    # =====================================================================
    def viewer_window_width_changed(self, value):
        """Apply the selected Window Width to the viewer."""
        self.viewer.set_window_width(value)

    def viewer_window_level_changed(self, value):
        """Apply the selected Window Level to the viewer."""
        self.viewer.set_window_level(value)

    # Segmentation
    # =====================================================================
    def start_segmentation(self):
        """
        Segment the structures ticked in the Segmentation tab.

        plan_runs() turns the ticked groups into the minimal list of
        TotalSegmentator runs. Only runs whose results are not on disk yet
        are executed. If everything already exists, the saved masks are
        simply loaded - nothing is recomputed unless the user ticks
        "Recompute even if results already exist".
        SegmentationWorker executes the runs outside the GUI thread.
        """
        if self.case_manager.ct_volume is None:
            return

        try:
            runs = plan_runs(self.segmentation_tab.selected_groups())
            case_dir = self.case_manager.get_results_directory()
        except Exception as error:
            QMessageBox.critical(self, "Segmentation Preparation Failed", str(error))
            return

        if self.segmentation_tab.force_rerun():
            runs_to_execute = runs                    # user asked to recompute
        else:
            runs_to_execute = missing_runs(runs, case_dir)

        if not runs_to_execute:
            # Everything selected already exists: just show it.
            self._load_masks_from_disk(keys_for_groups(self.segmentation_tab.selected_groups()))
            return

        try:
            self.statusBar().showMessage("Preparing segmentation input...")
            input_path = self.case_manager.prepare_segmentation_input()
        except Exception as error:
            QMessageBox.critical(self, "Segmentation Preparation Failed", str(error))
            return

        self._set_processing_state(True)
        self.segmentation_tab.set_progress(0, len(runs_to_execute), "Starting...")
        self.statusBar().showMessage("Running segmentation...")

        self.segmentation_thread = QThread()
        self.segmentation_worker = SegmentationWorker(
            input_path=input_path,
            output_dir=case_dir,
            runs=runs_to_execute,
        )

        # Run the worker outside the main GUI thread.
        self.segmentation_worker.moveToThread(self.segmentation_thread)

        self.segmentation_thread.started.connect(self.segmentation_worker.run)
        self.segmentation_worker.progress.connect(self.segmentation_progress)
        self.segmentation_worker.finished.connect(self.segmentation_finished)
        self.segmentation_worker.failed.connect(self.segmentation_failed)

        self.segmentation_worker.finished.connect(self.segmentation_thread.quit)
        self.segmentation_worker.failed.connect(self.segmentation_thread.quit)

        self.segmentation_thread.finished.connect(self.segmentation_worker.deleteLater)
        self.segmentation_thread.finished.connect(self.segmentation_thread.deleteLater)

        self.segmentation_thread.start()

    def segmentation_progress(self, step, total, message):
        """Show which model is currently running."""
        self.segmentation_tab.set_progress(step, total, message)
        self.statusBar().showMessage(message)

    def segmentation_finished(self, results):
        """Load and display newly generated segmentations.

        results : dict {structure key: mask file path}
        """
        try:
            # Load the new files AND any already-saved ones the user ticked
            # (e.g. a liver computed earlier), straight from disk.
            keys = set(results) | set(
                keys_for_groups(self.segmentation_tab.selected_groups())
            )
            self.case_manager.get_existing_masks(keys)

            empty_labels = self._show_masks()

            message = "Segmentation completed."
            if empty_labels:
                message += " Nothing found for: " + ", ".join(empty_labels) + "."
            self.statusBar().showMessage(message)

        except Exception as error:
            QMessageBox.critical(self, "Unable to Display Segmentation", str(error))
            self.statusBar().showMessage(
                "Segmentation completed but the masks could not be displayed."
            )
        finally:
            self._set_processing_state(False)

    def segmentation_failed(self, error_message):
        """Display an error; keep whatever finished before the failure."""
        # The worker sends "summary\n\nfull traceback": show the summary,
        # keep the traceback behind the "Show Details..." button.
        summary, _, details = error_message.partition("\n\n")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Segmentation Failed")
        box.setText(summary)
        if details:
            box.setDetailedText(details)
        box.exec()
        self.statusBar().showMessage("Segmentation failed.")
        self._set_processing_state(False)

        # Runs that completed before the failure are already saved; clicking
        # the button again continues with only the missing ones.
        self.statusBar().showMessage(
            "Segmentation failed. Finished parts were saved - click again to continue."
        )

    def _set_processing_state(self, processing):
        """Enable or disable controls while segmentation is running."""
        has_volume = self.case_manager.ct_volume is not None

        self.data_tab.load_nifti_button.setEnabled(not processing)
        self.data_tab.load_dicom_button.setEnabled(not processing)
        self.data_tab.ww_control.setEnabled(has_volume and not processing)
        self.data_tab.wl_control.setEnabled(has_volume and not processing)
        self.segmentation_tab.segment_button.setEnabled(has_volume and not processing)
        self.segmentation_tab.set_processing(processing)

        if not processing:
            self.segmentation_tab.hide_progress()
            self._refresh_segment_button()