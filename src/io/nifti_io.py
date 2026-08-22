#this image_io.py is responsible for saving and loading different medical image formats.
import os
import SimpleITK as sitk
from ..core.medical_volume import MedicalVolume


def load_nifti(input_path):
    """
    Load a NIfTI image and return it as a MedicalVolume.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
   
    image = sitk.ReadImage(input_path)


    return MedicalVolume(
        voxel_data=sitk.GetArrayFromImage(image),
        spacing=image.GetSpacing(),
        origin=image.GetOrigin(),
        direction=image.GetDirection(),
    )




def save_nifti(volume, output_path):
    """
    Save a MedicalVolume object as a NIfTI file.
    """
    image = sitk.GetImageFromArray(volume.voxel_data)


    image.SetSpacing(volume.spacing)
    image.SetOrigin(volume.origin)
    image.SetDirection(volume.direction)


    sitk.WriteImage(image, output_path)




