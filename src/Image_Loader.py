import SimpleITK as sitk

from src.medical_volume import MedicalVolume
def load_dicom(folder_path):
    reader = sitk.ImageSeriesReader()
    series_ids = reader.GetGDCMSeriesIDs(folder_path)
    if not series_ids:
        raise ValueError(f"No DICOM series found in folder: {folder_path}")  #defensive programming , avoid errors
    dicom_names = reader.GetGDCMSeriesFileNames(folder_path, series_ids[0])
    reader.SetFileNames(dicom_names)
    image = reader.Execute()
    voxel_data = sitk.GetArrayFromImage(image)
    spacing = image.GetSpacing()
    origin = image.GetOrigin()
    direction = image.GetDirection()
    return MedicalVolume(voxel_data=voxel_data, spacing=spacing, origin=origin, direction=direction)
     #or volume= MedicalVolume(voxel_data=voxel_data, spacing=spacing, origin=origin, direction=direction) then return volume.

