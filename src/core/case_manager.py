# This module stores information about the medical volume loaded in the application.
# The CaseManager keeps patient/case data management separate from the GUI.

from pathlib import Path
from src.io.nifti_io import load_nifti, save_nifti

class CaseManager: # The source may be either a NIfTI volume or a DICOM folder.
  
    def __init__(self):
        #Initialize the application with no active medical case.
        self.source_type = None
        self.source_path = None
        self.ct_volume = None
        self.liver_mask = None
        self.segmentation_input_path = None
    def clear(self):
    #Clear all information belonging to the currently loaded case.

      self.source_type = None
      self.source_path = None
      self.ct_volume = None
      self.liver_mask = None
      self.segmentation_input_path = None
    
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
        #Returns the path to the resulting directory 
        results_directory = Path("results")
        results_directory.mkdir(parents=True, exist_ok=True)
        return results_directory

    def get_liver_mask_path(self):
        #Return the liver-mask path associated with the current input.

        source_name = self._get_source_name()
        return self.get_results_directory() / f"liver_{source_name}.nii.gz"
#----------------------------------------
# Existing segmentation

    def get_existing_liver_mask(self):
        #Return a previously generated liver mask if available and compatible with the current CT.
        # The mask is reused only if its array dimensions match those of the currently loaded CT.

        if self.ct_volume is None:
            return None

        liver_mask_path = self.get_liver_mask_path()

        if not liver_mask_path.exists():
            return None

        mask_volume = load_nifti(str(liver_mask_path))

        # A mask belonging to a geometrically different volume must not be displayed over the current CT.
        if mask_volume.voxel_data.shape != self.ct_volume.voxel_data.shape:
            return None

        self.liver_mask = mask_volume
        return mask_volume

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

    def set_liver_mask(self, mask_volume):
        """
        Store a liver segmentation for the current CT.

        Parameters
        ----------
        mask_volume : MedicalVolume
            Liver segmentation corresponding to the active CT volume.
        """
        if self.ct_volume is None:
            raise RuntimeError("Cannot assign a liver mask because no CT volume is loaded.")

        if mask_volume.voxel_data.shape != self.ct_volume.voxel_data.shape:
            raise ValueError("The liver-mask dimensions do not match the CT volume.")

        self.liver_mask = mask_volume