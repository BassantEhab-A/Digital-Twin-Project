"""
Background liver-segmentation worker.

TotalSegmentator can take several minutes to process a CT volume,
especially when running on the CPU. Running segmentation directly
inside the GUI thread would freeze the application.

This worker performs the segmentation in a separate Qt thread and
communicates the result back to the main window through Qt signals.
"""

from PySide6.QtCore import QObject, Signal, Slot

from src.segmentation_module.segmentation import segment_liver


class SegmentationWorker(QObject):
    """
    Run liver segmentation outside the main GUI thread.

    Parameters
    ----------
    input_path : str or Path
        NIfTI CT volume that will be segmented.

    output_mask_path : str or Path
        Full path (including filename) where the liver mask should be
        written. CaseManager is responsible for choosing this path.
    """

    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, input_path, output_mask_path):
        super().__init__()
        self.input_path = input_path
        self.output_mask_path = output_mask_path

    @Slot()
    def run(self):
        """Execute TotalSegmentator and report success or failure."""
        try:
            mask_path = segment_liver(
                input_path=self.input_path,
                output_mask_path=self.output_mask_path,
            )
            self.finished.emit(mask_path)
        except Exception as error:
            self.failed.emit(str(error))