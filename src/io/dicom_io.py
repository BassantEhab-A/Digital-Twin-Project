"""
DICOM loader with recursive series discovery and metadata extraction.
"""

import traceback
import SimpleITK as sitk
from pathlib import Path

from src.core.medical_volume import MedicalVolume


def _find_series_directory(folder_path):
    """Return the directory that actually contains a DICOM series."""
    folder_path = Path(folder_path)

    if sitk.ImageSeriesReader.GetGDCMSeriesIDs(str(folder_path)):
        return folder_path

    for subfolder in sorted(folder_path.rglob("*")):
        if subfolder.is_dir():
            if sitk.ImageSeriesReader.GetGDCMSeriesIDs(str(subfolder)):
                return subfolder

    return None


def _read_metadata(dicom_names):
    """Extract useful tags from the first DICOM slice."""
    metadata = {}
    if not dicom_names:
        return metadata

    try:
        import pydicom
        ds = pydicom.dcmread(dicom_names[0], stop_before_pixels=True)

        for tag in (
            "StudyDescription",
            "SeriesDescription",
            "PatientID",
            "PatientName",
            "Modality",
            "BodyPartExamined",
        ):
            value = getattr(ds, tag, "")
            metadata[tag] = str(value) if value is not None else ""
    except Exception as error:
        print(f"[load_dicom] Metadata read failed: {error}")

    return metadata


def load_dicom(folder_path):
    print(f"[load_dicom] Looking for DICOM series in: {folder_path}")

    series_directory = _find_series_directory(folder_path)

    if series_directory is None:
        raise ValueError(
            f"No DICOM series found in: {folder_path}\n"
            "Make sure you selected the folder that directly contains "
            "the DICOM slice files (e.g., image_0, image_1, ...)."
        )

    print(f"[load_dicom] Found series in: {series_directory}")

    reader = sitk.ImageSeriesReader()
    series_ids = reader.GetGDCMSeriesIDs(str(series_directory))

    if not series_ids:
        raise ValueError(
            f"SimpleITK returned no series IDs for {series_directory}"
        )

    dicom_names = reader.GetGDCMSeriesFileNames(
        str(series_directory), series_ids[0]
    )
    print(f"[load_dicom] {len(dicom_names)} slices in series")

    metadata = _read_metadata(dicom_names)

    reader.SetFileNames(dicom_names)

    try:
        image = reader.Execute()
    except Exception:
        print("[load_dicom] SimpleITK failed to read the series:")
        traceback.print_exc()
        raise

    print(f"[load_dicom] Loaded image. Size: {image.GetSize()}")
    print(f"[load_dicom] Pixel type: {image.GetPixelIDTypeAsString()}")

    spacing = image.GetSpacing()
    origin = image.GetOrigin()
    direction = image.GetDirection()

    voxel_data = sitk.GetArrayFromImage(image)
    print(f"[load_dicom] Array shape: {voxel_data.shape}, "
          f"memory: {voxel_data.nbytes / (1024 ** 2):.1f} MB")

    del image

    return MedicalVolume(
        voxel_data=voxel_data,
        spacing=spacing,
        origin=origin,
        direction=direction,
        metadata=metadata,
    )