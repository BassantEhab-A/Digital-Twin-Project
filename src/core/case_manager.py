"""State of the currently loaded case, kept separate from the GUI.

The source may be a NIfTI volume or a DICOM folder. Original masks stored in
`masks` are never modified by a resection simulation.
"""
from __future__ import annotations

from pathlib import Path

from src.core.structures import (SEGMENTABLE, STRUCTURE_BY_KEY, mask_filename)
from src.io.nifti_io import load_nifti, save_nifti

RESULTS_ROOT = Path("results")


class CaseManager:
    def __init__(self, results_root: Path | str = RESULTS_ROOT):
        self.results_root = Path(results_root)
        self.clear()

    def clear(self) -> None:
        """Forget everything about the current case."""
        self.source_type = None            # "nifti" | "dicom"
        self.source_path = None
        self.ct_volume = None
        self.masks = {}                    # structure key -> MedicalVolume (binary)
        self.segmentation_input_path = None

    @property
    def liver_mask(self):
        return self.masks.get("liver")

    # ---------------------------------------------------- register loaded data
    def set_nifti_case(self, file_path, volume) -> None:
        self.clear()
        self.source_type = "nifti"
        self.source_path = Path(file_path)
        self.ct_volume = volume
        self.segmentation_input_path = self.source_path   # TotalSegmentator reads it directly

    def set_dicom_case(self, folder_path, volume) -> None:
        self.clear()
        self.source_type = "dicom"
        self.source_path = Path(folder_path)
        self.ct_volume = volume                            # converted to NIfTI on demand

    # --------------------------------------------------------------- paths
    def _source_name(self) -> str:
        if self.source_path is None:
            raise RuntimeError("No medical case is currently loaded.")
        if self.source_type == "dicom":
            return self.source_path.name
        name = self.source_path.name
        # Path.stem would leave ".nii" for "x.nii.gz".
        for suffix in (".nii.gz", ".nii"):
            if name.lower().endswith(suffix):
                return name[: -len(suffix)]
        return self.source_path.stem

    def get_results_directory(self, create: bool = True) -> Path:
        case_dir = self.results_root / self._source_name()
        if create:
            case_dir.mkdir(parents=True, exist_ok=True)
        return case_dir

    def get_mask_path(self, key: str, create_dir: bool = True) -> Path:
        """e.g. results/<case>/liver_tumor.nii.gz"""
        if key not in STRUCTURE_BY_KEY:
            raise KeyError(f"Unknown structure: {key}")
        return self.get_results_directory(create_dir) / mask_filename(key)

    # ------------------------------------------------- existing segmentation
    def existing_mask_keys(self) -> list:
        """Keys that already have a mask file on disk (nothing is loaded)."""
        if self.source_path is None:
            return []
        return [s.key for s in SEGMENTABLE
                if self.get_mask_path(s.key, create_dir=False).exists()]

    def get_existing_masks(self, keys=None) -> dict:
        """Load saved masks from disk into `self.masks`; return those loaded now.

        A mask is used only if its array shape equals the CT's. One unreadable
        file does not stop the others.
        """
        if self.ct_volume is None:
            return {}

        wanted = None if keys is None else set(keys)
        found = {}
        for structure in SEGMENTABLE:
            if wanted is not None and structure.key not in wanted:
                continue
            path = self.get_mask_path(structure.key, create_dir=False)
            if not path.exists():
                continue
            try:
                mask = load_nifti(str(path))
            except Exception as error:
                print(f"[CaseManager] Could not read {path.name}: {error}")
                continue
            if mask.shape != self.ct_volume.shape:
                print(f"[CaseManager] {path.name} does not match this CT - skipped.")
                continue
            found[structure.key] = mask

        self.masks.update(found)
        return found

    # ------------------------------------------------- segmentation input
    def prepare_segmentation_input(self) -> Path:
        """A NIfTI file TotalSegmentator can read (DICOM is converted once)."""
        if self.ct_volume is None:
            raise RuntimeError("No medical volume is currently loaded.")

        if self.source_type == "nifti":
            return self.segmentation_input_path
        if self.source_type == "dicom":
            nifti_path = self.get_results_directory() / f"input_{self._source_name()}.nii.gz"
            if not nifti_path.exists():
                save_nifti(self.ct_volume, str(nifti_path))
            self.segmentation_input_path = nifti_path
            return nifti_path
        raise RuntimeError("The current medical-image source type is unsupported.")

    # ------------------------------------------------- segmentation result
    def set_mask(self, key: str, mask_volume) -> None:
        if self.ct_volume is None:
            raise RuntimeError("Cannot assign a mask because no CT volume is loaded.")
        if key not in STRUCTURE_BY_KEY:
            raise KeyError(f"Unknown structure: {key}")
        if mask_volume.shape != self.ct_volume.shape:
            raise ValueError(f"The '{key}' mask dimensions do not match the CT volume.")
        self.masks[key] = mask_volume
