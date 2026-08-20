"""  This module is intentionally kept small. Its only responsibility is to create the Qt application, create the main window,
    and start the GUI event loop.

    Medical-image loading, visualization, and segmentation are implemented in separate modules so that the application can
    grow without turning main.py into a large monolithic script.  """


import os
# Tell Matplotlib to use PySide6 as its Qt binding.
# This must be defined before importing Matplotlib/Qt-based viewer modules,
# especially because both PyQt5 and PySide6 may exist in the environment.
os.environ["QT_API"] = "PySide6"


# Limit the number of CPU threads used by numerical libraries and nnU-Net.
# These settings helped keep TotalSegmentator memory usage manageable.
os.environ["nnUNet_n_proc_DA"] = "0"
os.environ["nnUNet_n_proc_preprocessing"] = "0"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"


from PySide6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

def main():
    """Create and launch the Liver Digital Twin application."""

    app = QApplication([])
    window = MainWindow()
    window.show()
    
    app.exec()

if __name__ == "__main__":
    main()

