import SimpleITK as sitk

from core.medical_volume import MedicalVolume


def load_dicom(folder_path):

    reader = sitk.ImageSeriesReader()

    series_ids = reader.GetGDCMSeriesIDs(folder_path)

    if not series_ids:
        raise ValueError(
            f"No DICOM series found in folder: {folder_path}"
        )

    dicom_names = reader.GetGDCMSeriesFileNames(
        folder_path,
        series_ids[0]
    )

    reader.SetFileNames(dicom_names)

    print("Reading DICOM series...")
    image = reader.Execute()

    print("DICOM series loaded.")
    print("Pixel type:", image.GetPixelIDTypeAsString())
    print("Image size:", image.GetSize())

    spacing = image.GetSpacing()
    origin = image.GetOrigin()
    direction = image.GetDirection()

    print("Converting image to NumPy array...")

    voxel_data = sitk.GetArrayFromImage(image)

    print("Array loaded.")
    print(
        "Array memory:",
        voxel_data.nbytes / (1024 ** 2),
        "MB"
    )

    # The SimpleITK image is no longer needed
    del image

    return MedicalVolume(
        voxel_data=voxel_data,
        spacing=spacing,
        origin=origin,
        direction=direction
    )