"""Resection tab: collects the user's choices and emits signals.

No geometry or volume maths lives here. MainWindow receives the signals,
runs the resection engine and updates the viewers.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QSlider, QVBoxLayout, QWidget,
)
from src.gui.tabs.scrollable import make_scrollable
from src.core.structures import (
    COUINAUD_KEYS, STRUCTURE_BY_KEY, TUMOR, VESSEL_KEY,
)

_STATUS_STYLE = {
    "idle": "padding: 8px; border-radius: 4px; background: #eee;",
    "safe": "padding: 8px; border-radius: 4px; background: #d4edda; color: #155724; font-weight: bold;",
    "unsafe": "padding: 8px; border-radius: 4px; background: #f8d7da; color: #721c24; font-weight: bold;",
}
MANUAL_POINTS_NEEDED = 3


class ResectionTab(QWidget):
    # --- signals to MainWindow ---
    planar_cut_requested = Signal(str, int, bool)   # orientation, position %, keep positive side
    anatomical_cut_requested = Signal(list)         # segment keys to remove
    manual_point_requested = Signal()               # "add the crosshair position as a point"
    manual_points_cleared = Signal()
    manual_cut_requested = Signal(bool)             # keep positive side
    suggest_requested = Signal(str)                 # "planar" | "anatomical"
    margin_changed = Signal(float)                  # mm
    reset_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.set_case(None, {})

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self._build_tumor_group())
        layout.addWidget(self._build_mode_group())
        layout.addWidget(self._build_planar_group())
        layout.addWidget(self._build_anatomical_group())
        layout.addWidget(self._build_manual_group())
        layout.addWidget(self._build_results_group())

        self.reset_btn = QPushButton("Reset simulation")
        self.reset_btn.clicked.connect(self.reset_requested.emit)
        layout.addWidget(self.reset_btn)
        layout.addStretch()
        self._on_mode_changed()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(make_scrollable(content))

    def _build_tumor_group(self):
        group = QGroupBox("Tumor margin and safety")
        form = QFormLayout(group)

        self.margin_spin = QDoubleSpinBox()
        self.margin_spin.setRange(0.0, 50.0)
        self.margin_spin.setSingleStep(1.0)
        self.margin_spin.setValue(10.0)
        self.margin_spin.setSuffix(" mm")
        self.margin_spin.setKeyboardTracking(False)     # emit when editing is finished
        self.margin_spin.valueChanged.connect(self.margin_changed.emit)
        form.addRow("Margin around tumor:", self.margin_spin)

        self.flr_spin = QDoubleSpinBox()
        self.flr_spin.setRange(10.0, 60.0)
        self.flr_spin.setValue(30.0)
        self.flr_spin.setSuffix(" %")
        self.flr_spin.setToolTip("Minimum future liver remnant (20 % healthy, 30 % after "
                                 "chemotherapy, 40 % cirrhotic liver).")
        form.addRow("Minimum remnant (FLR):", self.flr_spin)

        self.vessel_check = QCheckBox("Analyse vascular impact")
        self.vessel_check.setChecked(True)
        self.vessel_check.setToolTip("Finds severed portal / hepatic branches and the tissue "
                                     "that loses inflow or outflow. Needs the vessel segmentation.")
        form.addRow(self.vessel_check)
        return group

    def _build_mode_group(self):
        group = QGroupBox("Resection mode")
        box = QVBoxLayout(group)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Planar cut", "planar")
        self.mode_combo.addItem("Anatomical cut (Couinaud segments)", "anatomical")
        self.mode_combo.addItem("Manual cut (3 points)", "manual")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        box.addWidget(self.mode_combo)
        return group

    def _build_planar_group(self):
        self.planar_group = QGroupBox("Planar cut")
        form = QFormLayout(self.planar_group)

        self.axis_combo = QComboBox()
        self.axis_combo.addItem("Axial (horizontal)", "axial")
        self.axis_combo.addItem("Coronal (front / back)", "coronal")
        self.axis_combo.addItem("Sagittal (left / right)", "sagittal")
        form.addRow("Orientation:", self.axis_combo)

        self.keep_combo = QComboBox()
        self.keep_combo.addItem("Keep positive side (+)", True)
        self.keep_combo.addItem("Keep negative side (-)", False)
        form.addRow("Keep side:", self.keep_combo)

        self.pos_slider = QSlider(Qt.Horizontal)
        self.pos_slider.setRange(0, 100)
        self.pos_slider.setValue(50)
        self.pos_label = QLabel("50 %")
        self.pos_slider.valueChanged.connect(lambda v: self.pos_label.setText(f"{v} %"))
        row = QHBoxLayout()
        row.addWidget(self.pos_slider, 1)
        row.addWidget(self.pos_label)
        form.addRow("Position:", row)

        self.apply_planar_btn = QPushButton("Apply planar cut")
        self.apply_planar_btn.clicked.connect(self._emit_planar_cut)
        self.suggest_planar_btn = QPushButton("Suggest plane from tumor + margin")
        self.suggest_planar_btn.clicked.connect(lambda: self.suggest_requested.emit("planar"))
        form.addRow(self.apply_planar_btn)
        form.addRow(self.suggest_planar_btn)
        return self.planar_group

    def _build_anatomical_group(self):
        self.anatomical_group = QGroupBox("Anatomical cut")
        box = QVBoxLayout(self.anatomical_group)

        self.segment_checks = {}
        for key in COUINAUD_KEYS:
            check = QCheckBox(STRUCTURE_BY_KEY[key].label)
            self.segment_checks[key] = check
            box.addWidget(check)

        self.apply_anat_btn = QPushButton("Apply anatomical cut")
        self.apply_anat_btn.clicked.connect(self._emit_anatomical_cut)
        self.suggest_anat_btn = QPushButton("Suggest segments from tumor + margin")
        self.suggest_anat_btn.clicked.connect(lambda: self.suggest_requested.emit("anatomical"))
        box.addWidget(self.apply_anat_btn)
        box.addWidget(self.suggest_anat_btn)
        return self.anatomical_group

    def _build_manual_group(self):
        self.manual_group = QGroupBox("Manual cut")
        box = QVBoxLayout(self.manual_group)
        box.addWidget(self._wrapped_label(
            "Move the crosshair in the 2D views, then add the point. "
            "Three points define the cutting plane."))

        self.manual_points_label = QLabel()
        self.add_point_btn = QPushButton("Add crosshair position as point")
        self.add_point_btn.clicked.connect(self.manual_point_requested.emit)
        self.clear_points_btn = QPushButton("Clear points")
        self.clear_points_btn.clicked.connect(self.manual_points_cleared.emit)

        self.manual_keep_combo = QComboBox()
        self.manual_keep_combo.addItem("Keep side the normal points to", True)
        self.manual_keep_combo.addItem("Keep the opposite side", False)
        self.apply_manual_btn = QPushButton("Apply manual cut")
        self.apply_manual_btn.clicked.connect(
            lambda: self.manual_cut_requested.emit(self.manual_keep_combo.currentData()))

        for widget in (self.manual_points_label, self.add_point_btn, self.clear_points_btn,
                       self.manual_keep_combo, self.apply_manual_btn):
            box.addWidget(widget)
        self.set_manual_points(0)
        return self.manual_group

    def _build_results_group(self):
        group = QGroupBox("Resection results")
        form = QFormLayout(group)
        self._result_labels = {}
        for key, caption in (("cut", "Cut:"), ("original", "Liver volume:"),
                             ("remnant", "Remnant volume:"), ("flr", "Future liver remnant:"),
                             ("removed", "Removed volume:"), ("tumor", "Tumor volume:"),
                             ("margin", "Margin (achieved / required):"),
                             ("branches", "Severed branches:"),
                             ("territory", "Ischemic / congested:"),
                             ("effective", "Effective FLR:")):
            label = QLabel("—")
            label.setWordWrap(True)
            self._result_labels[key] = label
            form.addRow(caption, label)

        self.safety_label = self._wrapped_label("")
        form.addRow(self.safety_label)
        self._set_status("Awaiting simulation...", "idle")
        return group

    @staticmethod
    def _wrapped_label(text):
        label = QLabel(text)
        label.setWordWrap(True)
        return label

    # ------------------------------------------------------------- queries
    def margin_mm(self) -> float:
        return self.margin_spin.value()

    def flr_threshold(self) -> float:
        return self.flr_spin.value()

    def analyze_vessels(self) -> bool:
        return self.vessel_check.isEnabled() and self.vessel_check.isChecked()

    # --------------------------------------------------------------- slots
    def _on_mode_changed(self):
        mode = self.mode_combo.currentData()
        self.planar_group.setVisible(mode == "planar")
        self.anatomical_group.setVisible(mode == "anatomical")
        self.manual_group.setVisible(mode == "manual")

    def _emit_planar_cut(self):
        self.planar_cut_requested.emit(
            self.axis_combo.currentData(), self.pos_slider.value(), self.keep_combo.currentData())

    def _emit_anatomical_cut(self):
        selected = [k for k, c in self.segment_checks.items() if c.isChecked()]
        if not selected:
            self._set_status("Select at least one segment to remove.", "idle")
            return
        self.anatomical_cut_requested.emit(selected)

    # ----------------------------------------------------------- updates
    def set_case(self, ct_volume, masks):
        """Enable the controls that the loaded data allows."""
        has_liver = ct_volume is not None and "liver" in masks
        tumor = masks.get(TUMOR)
        has_tumor = has_liver and tumor is not None and bool(tumor.voxel_data.any())
        has_segments = has_liver and all(k in masks for k in COUINAUD_KEYS)
        vessels = masks.get(VESSEL_KEY)
        has_vessels = has_liver and vessels is not None and bool(vessels.voxel_data.any())

        self.apply_planar_btn.setEnabled(has_liver)
        self.apply_manual_btn.setEnabled(has_liver)
        self.add_point_btn.setEnabled(has_liver)
        self.reset_btn.setEnabled(has_liver)
        self.vessel_check.setEnabled(has_vessels)
        self.suggest_planar_btn.setEnabled(has_tumor)
        self.apply_anat_btn.setEnabled(has_segments)
        self.suggest_anat_btn.setEnabled(has_segments and has_tumor)

        self.suggest_planar_btn.setToolTip("" if has_tumor else "Needs a tumor segmentation.")
        self.suggest_anat_btn.setToolTip(
            "" if has_segments and has_tumor else "Needs tumor and Couinaud segmentations.")
        if not has_liver:
            self._set_status("Load a CT and a liver segmentation first.", "idle")

    def set_manual_points(self, count: int):
        self.manual_points_label.setText(f"Points: {count} / {MANUAL_POINTS_NEEDED}")
        self.apply_manual_btn.setEnabled(count >= MANUAL_POINTS_NEEDED and self.add_point_btn.isEnabled())

    def set_selected_segments(self, keys):
        keys = set(keys)
        for key, check in self.segment_checks.items():
            check.setChecked(key in keys)

    def show_message(self, text: str):
        self._set_status(text, "idle")

    def display_result(self, result):
        labels = self._result_labels
        labels["cut"].setText(result.cut_description or "—")
        labels["original"].setText(f"{result.original_volume_ml:,.1f} mL")
        labels["remnant"].setText(f"{result.remnant_volume_ml:,.1f} mL ({result.remnant_percentage:.1f} %)")
        labels["flr"].setText(f"{result.flr_percentage:.1f} %")
        labels["removed"].setText(f"{result.removed_volume_ml:,.1f} mL")
        if result.tumor_volume_ml > 0:
            labels["tumor"].setText(f"{result.tumor_volume_ml:,.1f} mL")
            achieved = result.margin_achieved_mm
            labels["margin"].setText(
                f"{'—' if achieved is None else f'{achieved:.1f}'} / {result.margin_required_mm:g} mm")
        else:
            labels["tumor"].setText("none segmented")
            labels["margin"].setText("—")

        vascular = result.vascular
        if vascular is None:
            for key in ("branches", "territory", "effective"):
                labels[key].setText("—")
        else:
            labels["branches"].setText(f"{vascular.severed_portal} portal, {vascular.severed_hepatic} hepatic"
                                       f" ({len(vascular.branches)} affected incl. downstream)")
            labels["territory"].setText(f"{vascular.ischemic_ml:,.1f} / {vascular.congested_ml:,.1f} mL")
            labels["effective"].setText(f"{result.effective_flr_percentage:.1f} %")

        text = result.safety_message
        if result.warnings:
            text += "\n" + "\n".join(result.warnings)
        ok = result.is_safe and result.tumor_covered and result.margin_satisfied
        self._set_status(text, "safe" if ok else "unsafe")

    def clear_results(self):
        for label in self._result_labels.values():
            label.setText("—")
        self._set_status("Awaiting simulation...", "idle")

    def _set_status(self, text, kind):
        self.safety_label.setText(text)
        self.safety_label.setStyleSheet(_STATUS_STYLE[kind])
