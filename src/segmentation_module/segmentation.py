"""Run TotalSegmentator tasks and collect their binary masks.
 
One call to `run_segmentation_task` executes one `Run` (see
src.core.structures.plan_runs) and leaves one `<key>.nii.gz` per structure
in the case's results directory."""
from __future__ import annotations
from pathlib import Path
import inspect ,json, os, shutil
import SimpleITK as sitk
from src.core.stuctures import STRUCTURE_BY_KEY, mask_filename

def _totalseg_config_path() -> Path:
    """Where TotalSegmentator keeps its settings file.
 
    TotalSegmentator uses $TOTALSEG_HOME_DIR if set, else ~/.totalsegmentator
    (it uses /tmp instead of /root when running as root, e.g. in Docker).
    """
    env_dir = os.environ.get("TOTALSEG_HOME_DIR")
    if env_dir:
        base = Path(env_dir)
    else:
        home = Path.home()
        base = (Path("/tmp") if str(home) == "/root" else home) / ".totalsegmentator"
    return base / "config.json"
 
 
def repair_totalseg_config():
    """Fix a corrupted TotalSegmentator settings file.
 
    TotalSegmentator reads config.json at the start of EVERY run. If that
    file is empty or damaged (e.g. the app was killed while it was being
    written) every run fails with
    "JSONDecodeError: Expecting value: line 1 column 1 (char 0)".
    TotalSegmentator recreates the file when it is missing, so a damaged one
    is moved aside as config.json.corrupt.
 
    Returns the path that was repaired, or None if nothing was wrong.
    """
    path = _totalseg_config_path()
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            json.load(handle)
        return None                       # valid JSON: leave it alone
    except (ValueError, UnicodeDecodeError):   # JSONDecodeError is a ValueError
        backup = path.with_name(path.name + ".corrupt")
        try:
            path.replace(backup)
        except OSError:
            path.unlink(missing_ok=True)
        print(f"[segmentation] Repaired corrupted settings file: {path}")
        return path
 
 
def _contains_memory_error(error) -> bool:
    """True if a MemoryError appears anywhere in the exception chain.
 
    Python chains exceptions ("During handling of the above exception,
    another exception occurred"). The error that finally surfaces is often
    only a symptom - the root cause is further up the chain.
    """
    seen = set()
    while error is not None and id(error) not in seen:
        if isinstance(error, MemoryError):
            return True
        seen.add(id(error))
        error = error.__cause__ or error.__context__
    return False
 
 
def _low_memory_options(func) -> dict:
    """Options that make TotalSegmentator use fewer parallel workers.
 
    By default it saves results with 6 worker processes, and EACH one loads
    the whole segmentation as float64 (512x512x129 voxels = ~270 MB). That
    can exhaust RAM on a laptop. One worker is slightly slower but safe.
    Options are only passed if the installed version knows them.
    """
    accepted = inspect.signature(func).parameters
    wanted = {"nr_thr_resamp": 1, "nr_thr_saving": 1}
    return {k: v for k, v in wanted.items() if k in accepted}
 
 
def _write_empty_mask(reference_path, destination) -> None:
    """Write an all-zero mask with the same geometry as the input CT.
 
    Used when a model finds nothing (e.g. a patient with no tumors), so
    'nothing found' is stored explicitly instead of looking like 'not run'.
    """
    reader = sitk.ImageFileReader()
    reader.SetFileName(str(reference_path))
    reader.ReadImageInformation()          # header only - no pixel data
 
    empty = sitk.Image(list(reader.GetSize()), sitk.sitkUInt8)
    empty.SetSpacing(reader.GetSpacing())
    empty.SetOrigin(reader.GetOrigin())
    empty.SetDirection(reader.GetDirection())
    sitk.WriteImage(empty, str(destination))
 
 
def run_segmentation_task(input_path, output_dir, run, device="cpu", fast=False):
    """Execute one TotalSegmentator run.
 
    Parameters
    ----------
    input_path : CT volume in NIfTI format.
    output_dir : case results directory; masks are written as <key>.nii.gz.
    run        : src.core.structures.Run (task, expected outputs, roi_subset).
    device     : 'cpu' or 'gpu'. CPU by default to avoid GPU VRAM limits.
    fast       : lower-resolution model; only applied to the 'total' task.
 
    Returns
    -------
    dict[str, Path] mapping structure key -> mask file.
    """
    # Imported here, not at module top: it pulls in torch (slow, heavy), and
    # this keeps application start-up and unit tests light.
    from totalsegmentator.python_api import totalsegmentator
 
    repair_totalseg_config()      # see docstring: a broken config.json fails every run
 
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
 
    # TotalSegmentator writes into a directory; give each run its own
    # staging folder, then move the masks to their final names.
    staging = output_dir / f"_staging_{run.task}"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
 
    kwargs = dict(
        input=str(input_path),
        output=str(staging),
        task=run.task,
        device=device,
    )
    if run.roi_subset:
        kwargs["roi_subset"] = list(run.roi_subset)
    if fast and run.task == "total":
        kwargs["fast"] = True
    kwargs.update(_low_memory_options(totalsegmentator))
 
    print(f"[segmentation] task='{run.task}' on {input_path.name}")
    try:
        try:
            totalsegmentator(**kwargs)
        except Exception as error:
            if _contains_memory_error(error):
                raise RuntimeError(
                    f"Not enough memory (RAM) to run the '{run.task}' model. "
                    "Close other programs and try again; if it keeps "
                    "happening, increase the Windows page file (virtual "
                    "memory) or run on a machine with more RAM."
                ) from error
            raise
        return _collect_outputs(input_path, output_dir, staging, run)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
 
 
def _collect_outputs(input_path, output_dir, staging, run):
    results = {}
    for key in run.outputs:
        staged = staging / mask_filename(key)
        destination = output_dir / mask_filename(key)
 
        if staged.exists():
            if destination.exists():
                destination.unlink()
            staged.replace(destination)
        elif STRUCTURE_BY_KEY[key].required:
            raise FileNotFoundError(
                f"TotalSegmentator finished task '{run.task}' but did not "
                f"produce the required file {staged.name}."
            )
        else:
            print(f"[segmentation] '{key}' not produced - storing an empty mask.")
            _write_empty_mask(input_path, destination)
 
        results[key] = destination
    return results