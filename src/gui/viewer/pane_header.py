"""
Orientation bar and slice slider shown above each 2D pane.

The visual style mimics 3D Slicer's per-pane header:
    [colored background] [orientation letters] [slice slider] [position]
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSlider,
    QWidget,
)


# Color used for each pane's header bar.
PANE_COLORS = {
    "axial":    "#e84d4d",   # red
    "coronal":  "#4dbf4d",   # green
    "sagittal": "#e8e84d",   # yellow
    "three_d":  "#4d9ee8",   # blue
}


class PaneHeader(QWidget):
    """
    Header strip shown above each pane.

    Parameters
    ----------
    plane : str
        One of "axial", "coronal", "sagittal", "three_d".
    letters : str
        The orientation letters to display (e.g. "R A S L P I").
        Pass an empty string to hide them (used by the 3D pane).
    """

    slider_moved = Signal(int)

    def __init__(self, plane, letters="", parent=None):
        super().__init__(parent)

        self.plane = plane
        self.setFixedHeight(22)
        color = PANE_COLORS.get(plane, "#888888")
        self.setStyleSheet(
            f"background-color: {color};"
            f"color: white;"
            f"font-family: monospace;"
            f"font-size: 11px;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(6)

        # --- orientation letters ---
        self.letters_label = QLabel(letters)
        self.letters_label.setStyleSheet("color: white; font-weight: bold;")
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
        self.position_label.setStyleSheet("color: white;")
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