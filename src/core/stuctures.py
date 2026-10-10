"""Single source of truth for every structure the app can segment and show.

Pure Python: no Qt, no torch. Everything else (planner, case manager,
viewers, UI) reads from this registry instead of hard-coding "liver".

To add a new structure: add one `Structure(...)` line below. Nothing else
needs to change.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# UI groups, in display order. Checkboxes in the Segmentation tab map to these.
GROUPS = {
    "liver": "Liver",
    "vessels": "Vessels",
    "tumors": "Tumors",
    "couinaud": "Couinaud segments",
}

# TotalSegmentator tasks, in the order we run them.
TASK_ORDER = ("total", "liver_vessels", "liver_segments")


@dataclass(frozen=True)
class Structure:
    key: str                      # TotalSegmentator class name == file stem
    label: str                    # text shown in the UI
    group: str                    # key of GROUPS
    task: str                     # TotalSegmentator task that produces it
    color: str                    # used in 2D overlay and 3D mesh
    layer: int                    # draw order in 2D (low = bottom)
    required: bool = False        # missing output = error (else = "not found")
    keep_largest: bool = False    # 3D: keep only the biggest connected piece
    default_visible: bool = True  # initial state of its display checkbox


@dataclass(frozen=True)
class Run:
    """One TotalSegmentator invocation."""
    task: str
    outputs: tuple                # structure keys this run must deliver
    roi_subset: tuple | None = None


_ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII")
_COUINAUD_COLORS = (
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8",
    "#f58231", "#911eb4", "#46f0f0", "#f032e6",
)


def _build_registry():
    items = [
        Structure("liver", "Liver", "liver", "total", "#d98c7a", 0,
                  required=True, keep_largest=True),
        # layer 1 = couinaud (drawn over liver, under vessels)
        Structure("liver_vessels", "Hepatic vessels", "vessels",
                  "liver_vessels", "#3b82f6", 2),
        Structure("portal_vein_and_splenic_vein", "Portal & splenic vein",
                  "vessels", "total", "#8b5cf6", 2),
        Structure("inferior_vena_cava", "Inferior vena cava", "vessels",
                  "total", "#06b6d4", 2),
        # Several separate lesions are normal -> never keep_largest.
        Structure("liver_tumor", "Liver tumors", "tumors",
                  "liver_vessels", "#ffd60a", 3),
    ]
    for i, (roman, color) in enumerate(zip(_ROMAN, _COUINAUD_COLORS), start=1):
        items.append(
            Structure(f"liver_segment_{i}", f"Segment {roman}", "couinaud",
                      "liver_segments", color, 1,
                      keep_largest=True, default_visible=False)
        )
    return tuple(items)


STRUCTURES = _build_registry()
STRUCTURE_BY_KEY = {s.key: s for s in STRUCTURES}


def mask_filename(key: str) -> str:
    return f"{key}.nii.gz"


def keys_for_groups(groups) -> list:
    """Structure keys that belong to the ticked groups (liver is always included)."""
    wanted = set(groups) | {"liver"}
    return [s.key for s in STRUCTURES if s.group in wanted]


def plan_runs(groups) -> list:
    """Turn the groups the user ticked into the minimal list of model runs.

    * The liver is always included (everything else is shown inside it).
    * `total` is restricted with roi_subset, so it stays fast.
    * `liver_vessels` yields vessels AND tumors in one run, so ticking either
      costs one run and both files are saved.
    """
    wanted = set(groups) | {"liver"}
    runs = []
    for task in TASK_ORDER:
        in_task = [s for s in STRUCTURES if s.task == task]
        selected = [s for s in in_task if s.group in wanted]
        if not selected:
            continue
        if task == "total":
            keys = tuple(s.key for s in selected)
            runs.append(Run(task, keys, roi_subset=keys))
        else:
            runs.append(Run(task, tuple(s.key for s in in_task), None))
    return runs


def missing_runs(runs, case_dir) -> list:
    """Runs whose result files are not all on disk yet."""
    case_dir = Path(case_dir)
    return [
        run for run in runs
        if any(not (case_dir / mask_filename(k)).exists() for k in run.outputs)
    ]