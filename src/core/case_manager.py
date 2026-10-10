# This module stores information about the medical volume loaded in the application.
# The CaseManager keeps patient/case data management separate from the GUI.

from pathlib import Path
from src.core.stuctures import STRUCTURE_BY_KEY, STRUCTURES, mask_filename
from src.io.nifti_io import load_nifti, save_nifti

class CaseManager: # The source may be either a NIfTI volume or a DICOM folder.
  
    def __init__(self):
        # Initialize the application with no active medical case.
        self.source_type = None
        self.source_path = None
        self.ct_volume = None
        # structure key -> MedicalVolume (binary mask). Keys come from
        # src.core.structures, e.g. "liver", "liver_tumor", "liver_segment_3".
        self.masks = {}
        self.segmentation_input_path = None
    
    def clear(self):
    # Clear all information belonging to the currently loaded case.
        self.source_type = None
        self.source_path = None
        self.ct_volume = None
        self.masks = {}
        self.segmentation_input_path = None

    @property
    def liver_mask(self):
        """Backward-compatible access to the liver mask."""
        return self.masks.get("liver")

# Register loaded data

    def set_nifti_case(self, file_path, volume):
         #Store a loaded NIfTI volume as the current case.
        
        self.clear()
        self.source_type = "nifti"
        self.source_path = Path(file_path)
        self.ct_volume = volume
        # TotalSegmentator can use the original NIfTI directly.
        self.segmentation_input_path = self.source_path

    def set_dicom_case(self, folder_path, volume):
        # Store a loaded DICOM series as the current case.

        self.clear()
        self.source_type = "dicom"
        self.source_path = Path(folder_path)
        self.ct_volume = volume
        # DICOM will be converted to NIfTI only if segmentation requires it.
        self.segmentation_input_path = None
#------------------------------------------------
# Output paths
    def _get_source_name(self):
        #Returns a simple name derived from the current input source.

        if self.source_path is None:
            raise RuntimeError("No medical case is currently loaded.")

        if self.source_type == "nifti":
            filename = self.source_path.name
            # pathlib.Path.stem only removes '.gz' from '.nii.gz',
            # so the compound NIfTI extension is handled explicitly.
            if filename.lower().endswith(".nii.gz"):
                return filename[:-7]
            return self.source_path.stem

        if self.source_type == "dicom":
            return self.source_path.name

        raise RuntimeError("Unknown medical-image source type.")
    
    def get_results_directory(self):
        if self.source_path is None:
             raise RuntimeError("No case loaded.")
        case_dir = Path("results") / self._get_source_name()
        case_dir.mkdir(parents=True, exist_ok=True)
        return case_dir
    def get_mask_path(self, key):
        """Path of the mask file for one structure, e.g. results/<case>/liver_tumor.nii.gz."""
        if key not in STRUCTURE_BY_KEY:
            raise KeyError(f"Unknown structure: {key}")
        return self.get_results_directory() / mask_filename(key)
 

    def get_liver_mask_path(self):
        #Return the liver-mask path associated with the current input.
        return self.get_mask_path("liver")
#----------------------------------------
# Existing segmentation
    def existing_mask_keys(self):
        """Keys of structures that already have a mask file on disk (nothing is loaded)."""
        if self.source_path is None:
            return []
        return [s.key for s in STRUCTURES if self.get_mask_path(s.key).exists()]
    def get_existing_masks(self, keys=None):
        """Load previously generated masks from disk and add them to self.masks.
 
        keys : structure keys to load (default: every structure that has a file).
 
        A mask is used only if its array shape equals the CT's; a mask from a
        geometrically different volume must never be shown over this CT.
        One unreadable file does not stop the others from loading.
        Returns the masks loaded by THIS call.
        """
        if self.ct_volume is None:
            return {}
 
        wanted = None if keys is None else set(keys)
        found = {}
        for structure in STRUCTURES:
            if wanted is not None and structure.key not in wanted:
                continue
            path = self.get_mask_path(structure.key)
            if not path.exists():
                continue
            try:
                mask = load_nifti(str(path))
            except Exception as error:
                print(f"[CaseManager] Could not read {path.name}: {error}")
                continue
            if mask.voxel_data.shape != self.ct_volume.voxel_data.shape:
                print(f"[CaseManager] {path.name} does not match this CT - skipped.")
                continue
            found[structure.key] = mask
 
        self.masks.update(found)          # merge: keep what is already loaded
        return found
 
    # =====================================================================
    # Segmentation input

    def prepare_segmentation_input(self):
  
        # Return a NIfTI file suitable for TotalSegmentator.
        # For NIfTI input, the original file is used directly.
        # For DICOM input, the already loaded MedicalVolume is converted internally to NIfTI. The user does not need to perform conversion manually.

        if self.ct_volume is None:
            raise RuntimeError("No medical volume is currently loaded.")

        # --------------------------------------------------------------
        # NIfTI
        # --------------------------------------------------------------
        if self.source_type == "nifti":
            return self.segmentation_input_path

        # --------------------------------------------------------------
        # DICOM
        # --------------------------------------------------------------
        if self.source_type == "dicom":
            source_name = self._get_source_name()
            nifti_path = self.get_results_directory() / f"input_{source_name}.nii.gz"

            # Avoid converting the same DICOM volume every time the user
            # requests segmentation.
            if not nifti_path.exists():
                save_nifti(self.ct_volume, str(nifti_path))

            self.segmentation_input_path = nifti_path
            return nifti_path

        raise RuntimeError("The current medical-image source type is unsupported.")

    # =====================================================================
    # Segmentation result

    def set_mask(self, key, mask_volume):
        """Store one structure's mask for the current CT."""
        if self.ct_volume is None:
            raise RuntimeError("Cannot assign a mask because no CT volume is loaded.")
        if key not in STRUCTURE_BY_KEY:
            raise KeyError(f"Unknown structure: {key}")
        if mask_volume.voxel_data.shape != self.ct_volume.voxel_data.shape:
            raise ValueError(f"The '{key}' mask dimensions do not match the CT volume.")
        self.masks[key] = mask_volume
 
    def set_liver_mask(self, mask_volume):
        # Kept for backward compatibility.
        self.set_mask("liver", mask_volume)