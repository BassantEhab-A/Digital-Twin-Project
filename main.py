from src.medical_volume import MedicalVolume
temporary_ct_data = "3D CT scan data"
volume = MedicalVolume(voxel_data=temporary_ct_data, spacing=(1.0, 1.0, 1.0), origin=(0.0, 0.0, 0.0), direction=(1.0, 0.0, 0.0), metadata={"patient_id": "12345", "scan_date": "2023-01-01"})
print(volume.voxel_data)  # Output: 3D CT scan data


from src.Image_Loader import load_dicom
from src.segmentation import LiverSegmentation
volume = load_dicom(r"C:\Users\Bassant\Downloads\Liver Digital Twin Project\User Experience\3Dircadb files Cases\PATIENT_DICOM\PATIENT_DICOM")
print("Voxel data shape:", volume.voxel_data.shape)
print("Spacing:", volume.spacing)
print("Origin:", volume.origin)

volume=load_dicom(r"C:\Users\Bassant\Downloads\Liver Digital Twin Project\User Experience\3Dircadb files Cases\PATIENT_DICOM\PATIENT_DICOM")
liver_segmentation = LiverSegmentation(liver_mask=None)
liver_mask = liver_segmentation.generate_ai_liver_mask(input_folder_path=r"C:\Users\Bassant\Downloads\Liver Digital Twin Project\User Experience\3Dircadb files Cases\PATIENT_DICOM\PATIENT_DICOM", output_directory_path=r"C:\Users\Bassant\Downloads\Liver Digital Twin Project\User Experience\3Dircadb files Cases\PATIENT_DICOM\PATIENT_DICOM")
calculated_liver_volume = liver_segmentation.calculate_liver_volume(volume.voxel_data, liver_mask, volume.spacing)
print("Calculated liver volume:", calculated_liver_volume)

import os
folder_path = r"C:\Users\Bassant\Downloads\Liver Digital Twin Project\User Experience\3Dircadb files Cases\PATIENT_DICOM\PATIENT_DICOM"
results_directory = os.path.join(folder_path, "segmentation_results")
volume =load_dicom(folder_path)
segmentation = LiverSegmentation(liver_mask=None)
liver_mask = segmentation.liverseg_bytotalseg(output_directory_path=results_directory)
print("AI segmentation completed. Liver mask shape:", liver_mask.shape)
print("Liver mask stored in volume.segmentations:", "liver" in volume.segmentations)