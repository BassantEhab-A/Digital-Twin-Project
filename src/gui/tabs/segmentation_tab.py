"""
Segmentation tab: choose what to segment, run it, and toggle what is displayed.

UI only - application logic stays in MainWindow. The tab is generated from the
registry in src.core.structures, so a new structure appears here automatically.
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.stuctures import GROUPS, STRUCTURES


class SegmentationTab(QWidget):
    """Controls for running segmentation and showing/hiding each structure."""

    # (structure key, visible)
    visibility_changed = Signal(str, bool)

    def __init__(self):
        super().__init__()
        self._available = set()   # keys that currently have a mask
        self._empty = set()       # ... of which nothing was found
        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ---- what to run -------------------------------------------------
        run_group = QGroupBox("Segment")
        run_layout = QVBoxLayout(run_group)

        self.group_checks = {}
        for group_key, group_label in GROUPS.items():
            check = QCheckBox(group_label)
            check.setChecked(True)
            if group_key == "liver":
                check.setEnabled(False)       # always needed
                check.setToolTip("The liver is always segmented.")
            self.group_checks[group_key] = check
            run_layout.addWidget(check)

        self.force_check = QCheckBox("Recompute even if results already exist")
        self.force_check.setToolTip(
            "Off (default): saved results are loaded from disk and only "
            "missing structures are computed."
        )
        run_layout.addWidget(self.force_check)

        self.segment_button = QPushButton("Run Segmentation")
        self.segment_button.setEnabled(False)
        run_layout.addWidget(self.segment_button)

        self.saved_label = QLabel("")
        self.saved_label.setWordWrap(True)
        self.saved_label.setStyleSheet("color: #2e7d32; font-size: 11px;")
        run_layout.addWidget(self.saved_label)

        self.hint_label = QLabel(
            "The first run downloads the models. On CPU, each model "
            "can take several minutes."
        )
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet("color: #666; font-size: 11px;")
        run_layout.addWidget(self.hint_label)

        self.progress_label = QLabel("")
        self.progress_label.setWordWrap(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_label.setVisible(False)
        self.progress_bar.setVisible(False)
        run_layout.addWidget(self.progress_label)
        run_layout.addWidget(self.progress_bar)

        # ---- what to display ------------------------------------------
        display_group = QGroupBox("Display")
        display_layout = QVBoxLayout(display_group)

        self.visibility_checks = {}
        current_group = None
        for structure in STRUCTURES:
            if structure.group != current_group:
                current_group = structure.group
                heading = QLabel(f"<b>{GROUPS[current_group]}</b>")
                display_layout.addWidget(heading)

            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 0, 0, 0)

            swatch = QLabel()
            swatch.setFixedSize(12, 12)
            swatch.setStyleSheet(
                f"background:{structure.color}; border:1px solid #555;"
            )
            check = QCheckBox(structure.label)
            check.setEnabled(False)           # until a mask exists
            check.toggled.connect(
                lambda checked, key=structure.key: self.visibility_changed.emit(key, checked)
            )
            self.visibility_checks[structure.key] = check

            row_layout.addWidget(swatch)
            row_layout.addWidget(check, 1)
            display_layout.addWidget(row)

        layout.addWidget(run_group)
        layout.addWidget(display_group)
        layout.addStretch()

    # ----------------------------------------------------------- queries
    def selected_groups(self) -> set:
        """Groups ticked in the 'Segment' box (liver is always included)."""
        return {g for g, c in self.group_checks.items() if c.isChecked()} | {"liver"}

    def force_rerun(self) -> bool:
        return self.force_check.isChecked()

    def set_saved_info(self, text: str) -> None:
        """One-line note about results already on disk for this volume."""
        self.saved_label.setText(text)

    def visible_keys(self) -> set:
        """Structures whose display checkbox is enabled and ticked."""
        return {
            k for k, c in self.visibility_checks.items()
            if c.isEnabled() and c.isChecked()
        }

    # ----------------------------------------------------------- updates
    def reset_results(self) -> None:
        """Forget all masks (a new CT was loaded)."""
        self._available.clear()
        self._empty.clear()
        for structure in STRUCTURES:
            check = self.visibility_checks[structure.key]
            check.blockSignals(True)
            check.setChecked(False)
            check.setEnabled(False)
            check.setText(structure.label)
            check.blockSignals(False)

    def set_available(self, keys, empty_keys) -> None:
        """Enable the display checkboxes of structures that now have a mask.

        A structure whose mask is empty (e.g. no tumors) stays disabled and
        is labelled '(none found)'. A structure that just became available
        gets its default visibility; one that already was keeps the user's
        choice.
        """
        keys, empty_keys = set(keys), set(empty_keys)
        for structure in STRUCTURES:
            if structure.key not in keys:
                continue
            check = self.visibility_checks[structure.key]
            check.blockSignals(True)
            if structure.key in empty_keys:
                check.setChecked(False)
                check.setEnabled(False)
                check.setText(f"{structure.label} (none found)")
            else:
                was_usable = (
                    structure.key in self._available
                    and structure.key not in self._empty
                )
                check.setEnabled(True)
                check.setText(structure.label)
                if not was_usable:
                    check.setChecked(structure.default_visible)
            check.blockSignals(False)
        self._available |= keys
        self._empty = (self._empty - keys) | empty_keys

    def set_processing(self, processing: bool) -> None:
        for group_key, check in self.group_checks.items():
            if group_key != "liver":
                check.setEnabled(not processing)
        self.force_check.setEnabled(not processing)

    def set_progress(self, step: int, total: int, message: str = "") -> None:
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(step)
        self.progress_label.setText(message)
        visible = 0 <= step < total
        self.progress_bar.setVisible(visible)
        self.progress_label.setVisible(visible)

    def hide_progress(self) -> None:
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)