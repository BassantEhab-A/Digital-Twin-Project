from src.medical_volume import MedicalVolume
temporary_ct_data = "3D CT scan data"
volume = MedicalVolume(voxel_data=temporary_ct_data, spacing=(1.0, 1.0, 1.0), origin=(0.0, 0.0, 0.0), direction=(1.0, 0.0, 0.0), metadata={"patient_id": "12345", "scan_date": "2023-01-01"})
print(volume.voxel_data)  # Output: 3D CT scan data



