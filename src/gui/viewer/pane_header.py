"""Orientation bar and slice slider shown above each pane."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout,QLabel,QSlider,QWidget,)
from sympy import ff


# Color used for each pane's header bar.
PANE_COLORS = {
    "axial":    "#e84d4d",   # red
    "coronal":  "#4dbf4d",   # green
    "sagittal": "#e8e84d",   # yellow
    "three_d":  "#4d9ee8",   # blue
}


class PaneHeader(QWidget):
    slider_moved = Signal(int)

    def __init__(self, plane, letters="", parent=None):
        super().__init__(parent)

        self.plane = plane
        self.setFixedHeight(22)
        self.setObjectName("PaneHeader")
        # A plain QWidget subclass ignores stylesheet backgrounds unless this
        # attribute is set -> the coloured bar was not being painted.
        self.setAttribute(Qt.WA_StyledBackground, True)
        color = PANE_COLORS.get(plane, "#888888")
        self.setStyleSheet(
            f"#PaneHeader {{ background-color: {color}; }}"
            "#PaneHeader QLabel { color: white; font-family: monospace; font-size: 11px; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(6)

        # --- orientation letters ---
        self.letters_label = QLabel(letters)
        self.letters_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.letters_label)

        # --- slice slider ---
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self.slider_moved.emit)
        layout.addWidget(self.slider, 1)

        # --- position label ---
        self.position_label = QLabel("0.0mm")
        self.position_label.setMinimumWidth(70)
        self.position_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.position_label)

    # ------------------------------------------------------------------ API
    def set_range(self, minimum, maximum):
        """Configure the slider bounds."""
        self.slider.blockSignals(True)
        self.slider.setRange(minimum, maximum)
        self.slider.setEnabled(maximum > minimum)
        self.slider.blockSignals(False)

    def set_value(self, value):
        """Move the slider without re-emitting the signal."""
        self.slider.blockSignals(True)
        self.slider.setValue(int(value))
        self.slider.blockSignals(False)

    def set_position_label(self, text):
        self.position_label.setText(text)