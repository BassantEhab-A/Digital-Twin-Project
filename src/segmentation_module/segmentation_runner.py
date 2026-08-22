"""Background liver-segmentation worker.
TotalSegmentator can take several minutes to process a CT volume,especially when running on the CPU. Running segmentation directly inside the GUI thread would freeze the application.
This worker performs the segmentation in a separate Qt thread and communicates the result back to the main window through Qt signals.
"""

from PySide6.QtCore import QObject, Signal, Slot
from ..segmentation_module import segment_liver
class SegmentationWorker(QObject):
    #Run liver segmentation outside the main GUI thread.
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, input_path, output_directory):
        #Store segmentation input and output locations.
        super().__init__()
        self.input_path = input_path
        self.output_directory = output_directory

    @Slot()
    def run(self):
        #Execute TotalSegmentator and report success or failure.
        try:
            mask_path = segment_liver(
                input_path=self.input_path,
                output_directory=self.output_directory)
            self.finished.emit(mask_path)
        except Exception as error:
            self.failed.emit(str(error))