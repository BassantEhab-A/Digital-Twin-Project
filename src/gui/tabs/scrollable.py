"""Reusable helper: wrap a tab's content in a vertical scroll area."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QSizePolicy, QWidget


def make_scrollable(content: QWidget, min_width: int = 320) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(content)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    area.setFrameShape(QScrollArea.NoFrame)
    area.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
    content.setMinimumWidth(min_width)
    return area