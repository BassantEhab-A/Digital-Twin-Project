from src.Image_Loader import load_dicom
folder_path =r"C:\Users\Bassant\Downloads\Liver Digital Twin Project\User Experience\3Dircadb files Cases\3Dircadb1.1\3Dircadb1.1\PATIENT_DICOM\PATIENT_DICOM"
print("Loading DICOM files from folder:", folder_path)
volume = load_dicom(folder_path)
#simple data extraction 
print("Voxel data shape:", volume.voxel_data.shape)
print("Spacing:", volume.spacing)
print("Origin:", volume.origin)
