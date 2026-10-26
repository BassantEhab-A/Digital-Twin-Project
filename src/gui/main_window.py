"""Main application window for the Liver Digital Twin.

Patient/case state and output-path management are handled by CaseManager.

Medical-image visualization is handled by QuadViewer.

Segmentation computation is handled outside the GUI by SegmentationWorker;
WHAT can be segmented is defined in src/core/structures.py.
"""

from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QMainWindow, QMessageBox,
    QStatusBar, QTabWidget, QWidget,
)

from src.core.case_manager import CaseManager
from src.core.resection import (
    PlaneCut, ResectionEngine, SegmentCut, VesselTree, expand_mask_mm,
    suggest_plane_cut, suggest_segment_cut,
)
from src.core.structures import (
    DEVASCULARIZED, IVC_KEY, PORTAL_KEY, RESECTED_LIVER, SEVERED_VESSELS,
    STRUCTURE_BY_KEY, TUMOR, TUMOR_MARGIN, VESSEL_KEY,
    keys_for_groups, missing_runs, plan_runs,
)
from src.gui.tabs import data_tab, resection_tab, segmentation_tab
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
        # Resection state. case_manager.masks always keeps the ORIGINAL masks;
        # the simulated result is overlaid only when building the display.
        self._resection_result = None
        self._margin_zone = None          # tumor dilated by the margin (bool array)
        self._manual_points = []          # picked points, patient coordinates (mm)
        self._vessel_tree = None          # built on first use, per case

        # References are kept while segmentation is running.
        self.segmentation_thread = None
        self.segmentation_worker = None

        self._configure_window()
        self._build_ui()

    # =====================================================================
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
        self.resection_tab = resection_tab.ResectionTab()

        self.tabs.addTab(self.data_tab, "Data")
        self.tabs.addTab(self.segmentation_tab, "Segmentation")
        self.tabs.addTab(self.resection_tab, "Resection")

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
       
        # Connect Resection tab signals
        tab = self.resection_tab
        tab.planar_cut_requested.connect(self._handle_planar_cut)
        tab.anatomical_cut_requested.connect(self._handle_anatomical_cut)
        tab.manual_point_requested.connect(self._add_manual_point)
        tab.manual_points_cleared.connect(self._clear_manual_points)
        tab.manual_cut_requested.connect(self._handle_manual_cut)
        tab.suggest_requested.connect(self._handle_suggestion)
        tab.margin_changed.connect(self._on_margin_changed)
        tab.reset_requested.connect(self._reset_resection)

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
        """Display a newly loaded CT and reset case-dependent UI state."""
        self.viewer.set_volume(volume)
        self.segmentation_tab.reset_results()

        # A new case invalidates any previous resection simulation.
        self._reset_resection_state()
        self.resection_tab.set_case(
            self.case_manager.ct_volume,
            self.case_manager.masks,
        )

        self._configure_controls_for_volume()
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
        """Refresh viewer and tabs after masks were loaded; return empty-structure labels."""
        masks = self.case_manager.masks
        empty = {key for key, mask in masks.items() if not mask.voxel_data.any()}

        # New masks may change the liver: an older simulation no longer applies.
        self._reset_resection_state()
        self.resection_tab.clear_results()
        self.segmentation_tab.set_available(set(masks), empty)
        self._update_margin_zone()
        self._refresh_viewer()
        self.resection_tab.set_case(self.case_manager.ct_volume, masks)

        return [STRUCTURE_BY_KEY[key].label for key in sorted(empty)]

    # =====================================================================
    # Display: original masks + (optional) resection overlay
    # =====================================================================
    def _display_masks(self) -> dict:
        """Masks to draw. Never modifies case_manager.masks."""
        masks = dict(self.case_manager.masks)
        liver = masks.get("liver")
        if liver is None:
            return masks

        if self._margin_zone is not None:
            masks[TUMOR_MARGIN] = liver.like(self._margin_zone)
        result = self._resection_result
        if result is not None:
            masks["liver"] = liver.like(result.retained_mask)
            masks[RESECTED_LIVER] = liver.like(result.removed_mask)
            if result.vascular is not None:
                masks[DEVASCULARIZED] = liver.like(result.vascular.devascularized_mask)
                masks[SEVERED_VESSELS] = liver.like(result.vascular.severed_vessel_mask)
        return masks

    def _refresh_viewer(self):
        masks = self._display_masks()
        visible = self.segmentation_tab.visible_keys() | {
            key for key in masks
            if STRUCTURE_BY_KEY[key].is_derived and STRUCTURE_BY_KEY[key].default_visible
        }
        self.viewer.set_masks(masks, visible)

    def _update_margin_zone(self):
        """Recompute tumor + margin (inside the liver) for the current margin setting."""
        masks = self.case_manager.masks
        liver, tumor = masks.get("liver"), masks.get(TUMOR)
        self._margin_zone = None
        if liver is None or tumor is None or not tumor.voxel_data.any():
            return
        inside = liver.voxel_data > 0
        zone = expand_mask_mm(tumor.voxel_data > 0, liver.spacing, self.resection_tab.margin_mm())
        self._margin_zone = zone & inside

    def _get_vessel_tree(self):
        """Vessel graph for the current case (built once, then reused). None if unavailable."""
        if self._vessel_tree is None:
            masks = self.case_manager.masks
            vessels = masks.get(VESSEL_KEY)
            if vessels is None or not vessels.voxel_data.any():
                return None
            self.statusBar().showMessage("Building the vessel graph...")
            self._vessel_tree = VesselTree.build(
                vessels, portal=masks.get(PORTAL_KEY), ivc=masks.get(IVC_KEY))
        return self._vessel_tree

    def _reset_resection_state(self):
        self._resection_result = None
        self._vessel_tree = None
        self._margin_zone = None
        self._manual_points = []
        self.resection_tab.set_manual_points(0)

    # =====================================================================
    # Resection simulation (logic only; maths is in src/core/resection)
    # =====================================================================
    def _run_cut(self, make_cut):
        """Build a cut with `make_cut(liver)`, simulate it and show the result."""
        masks = self.case_manager.masks
        liver = masks.get("liver")
        if liver is None:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            cut = make_cut(liver)
            vessel_tree = self._get_vessel_tree() if self.resection_tab.analyze_vessels() else None
            result = ResectionEngine.simulate(
                liver, cut, tumor=masks.get(TUMOR),
                margin_mm=self.resection_tab.margin_mm(),
                threshold_percent=self.resection_tab.flr_threshold(),
                vessel_tree=vessel_tree,
            )
        except ValueError as error:                 # bad user input, not a crash
            self.resection_tab.show_message(str(error))
            return
        finally:
            QApplication.restoreOverrideCursor()

        self._resection_result = result
        self.resection_tab.display_result(result)
        self._refresh_viewer()
        self.statusBar().showMessage(f"{result.cut_description}: FLR {result.flr_percentage:.1f} %.")

    def _handle_planar_cut(self, orientation: str, position: int, keep_positive: bool):
        self._run_cut(lambda liver: PlaneCut.axis_aligned(
            liver, orientation, position, keep_positive))

    def _handle_anatomical_cut(self, segment_keys: list):
        self._run_cut(lambda liver: SegmentCut(self.case_manager.masks, segment_keys))

    def _handle_manual_cut(self, keep_positive: bool):
        points = list(self._manual_points)

        def make_cut(_liver):
            if len(points) != 3:
                raise ValueError("Add three points first.")
            return PlaneCut.from_points(*points, keep_positive=keep_positive)

        self._run_cut(make_cut)

    def _handle_suggestion(self, mode: str):
        """Propose a cut that removes tumor + margin, then simulate it."""
        if self._margin_zone is None:
            self.resection_tab.show_message("No tumor segmented - nothing to plan around.")
            return
        zone = self._margin_zone

        def make_cut(liver):
            if mode == "planar":
                return suggest_plane_cut(liver, zone)
            cut = suggest_segment_cut(self.case_manager.masks, zone)
            self.resection_tab.set_selected_segments(cut.keys)
            return cut

        self._run_cut(make_cut)

    # ---- manual cut points -------------------------------------------------
    def _add_manual_point(self):
        ct = self.case_manager.ct_volume
        if ct is None:
            return
        x, y, z = self.viewer.crosshair
        self._manual_points = (self._manual_points + [ct.voxel_to_world([x, y, z])])[-3:]
        self.resection_tab.set_manual_points(len(self._manual_points))

    def _clear_manual_points(self):
        self._manual_points = []
        self.resection_tab.set_manual_points(0)

    # ---- margin / reset ----------------------------------------------------
    def _on_margin_changed(self, _margin_mm: float):
        if self.case_manager.liver_mask is None:
            return
        # A result computed with the old margin would be misleading.
        self._resection_result = None
        self.resection_tab.clear_results()
        self._update_margin_zone()
        self._refresh_viewer()

    def _reset_resection(self):
        """Back to the intact liver."""
        self._resection_result = None
        self._manual_points = []
        self.resection_tab.set_manual_points(0)
        self.resection_tab.clear_results()
        if self.case_manager.masks:
            self._refresh_viewer()
        self.statusBar().showMessage("Resection simulation reset.")

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