"""
Background liver-segmentation worker.

TotalSegmentator can take several minutes to process a CT volume,
especially when running on the CPU. Running segmentation directly
inside the GUI thread would freeze the application.

This worker performs the segmentation in a separate Qt thread and
communicates the result back to the main window through Qt signals.
"""
import traceback
from PySide6.QtCore import QObject, Signal, Slot
from src.segmentation_module.segmentation import run_segmentation_task


class SegmentationWorker(QObject):
    """
    Run a list of segmentation runs outside the main GUI thread.
 
    Parameters
    ----------
    input_path : str or Path
        NIfTI CT volume that will be segmented.
    output_dir : str or Path
        Case results directory (CaseManager chooses it).
    runs : list[Run]
        Model runs to execute, in order (see structures.plan_runs).
 
    Signals
    -------
    progress(step, total, message) : emitted before each run starts.
    finished(dict)                 : {structure key: mask Path} for all runs.
    failed(str)                    : 'ErrorType: message' + blank line + full
                                     traceback. Masks of runs that already
                                     completed stay on disk.
    """
 
    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, input_path, output_dir, runs, device=None):
        super().__init__()
        self.input_path = input_path
        self.output_dir = output_dir
        self.runs = list(runs)
        self.device = device
        
    @Slot()
    def run(self):
        """Execute TotalSegmentator and report success or failure."""
        results = {}
        try:
            total = len(self.runs)
            for index, run in enumerate(self.runs):
                self.progress.emit(
                    index, total,
                    f"Running '{run.task}' model ({index + 1}/{total})...",
                )
                results.update(
                    run_segmentation_task(
                        input_path=self.input_path,
                        output_dir=self.output_dir,
                        run=run,
                        device=self.device,
                    )
                )
            self.progress.emit(total, total, "Segmentation finished.")
            self.finished.emit(results)
        except Exception as error:
            details = traceback.format_exc()
            print(details)                       # also visible in the console
            self.failed.emit(f"{type(error).__name__}: {error}\n\n{details}")