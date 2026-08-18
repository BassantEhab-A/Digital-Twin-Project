import os
# Mandatory 8GB RAM Thread Optimizations (Must be at the absolute top)
# os.environ["nnUNet_n_proc_DA"] = "0"
# os.environ["OMP_NUM_THREADS"] = "1"
# os.environ["MKL_NUM_THREADS"] = "1"

# CRITICAL FIX: We must load base matplotlib and set the backend
# BEFORE importing pyplot or any other data libraries!
import matplotlib
matplotlib.use("QtAgg")  
import matplotlib.pyplot as plt

# check the interactive backend print("Matplotlib backend:", plt.get_backend())   plt.switch_backend("QtAgg")   print("Matplotlib backend after switch:", plt.get_backend())

import numpy as np

from src.Image_Loader import load_dicom
from src.image_io import load_nifti, save_nifti
from src.segmentation import segment_liver
# from src.medical_volume import MedicalVolume

folder_path = r"C:\Users\Bassant\Downloads\Liver Digital Twin Project\User Experience\3Dircadb files Cases\3Dircadb1.1\3Dircadb1.1\PATIENT_DICOM\PATIENT_DICOM"
input_path = "patient.nii.gz"


def visualize_overlay(ct_volume, mask_volume):
    """Generates an interactive axial slice overlay viewer."""
    ct_data = ct_volume.voxel_data
    mask_data = mask_volume.voxel_data

    num_slices = ct_data.shape[0]
    current_slice = num_slices // 2

    fig, ax = plt.subplots(figsize=(8, 8))
    fig.canvas.manager.set_window_title("Liver Digital Twin - Slice Overlay Viewer")

    vmin, vmax = -100, 200 # Soft tissue thresholds

    im_ct = ax.imshow(ct_data[current_slice, :, :], cmap="gray", vmin=vmin, vmax=vmax, origin="lower")
    
    masked_liver = np.ma.masked_where(mask_data[current_slice, :, :] == 0, mask_data[current_slice, :, :])
    im_mask = ax.imshow(masked_liver, cmap="Reds", alpha=0.4, vmin=0, vmax=1, origin="lower")

    ax.set_title(f"Slice {current_slice}/{num_slices - 1} | Use Arrow Keys or Mouse Wheel")
    ax.axis("off")

    def update_slice():
        ax.set_title(f"Slice {current_slice}/{num_slices - 1} | Use Arrow Keys or Mouse Wheel")
        im_ct.set_data(ct_data[current_slice, :, :])
        new_mask = mask_data[current_slice, :, :]
        im_mask.set_data(np.ma.masked_where(new_mask == 0, new_mask))
        fig.canvas.draw_idle()

    def handle_interaction(event):
        nonlocal current_slice
        if event.key == "up" or getattr(event, "button", None) == "up":
            if current_slice < num_slices - 1:
                current_slice += 1
                update_slice()
        elif event.key == "down" or getattr(event, "button", None) == "down":
            if current_slice > 0:
                current_slice -= 1
                update_slice()

    fig.canvas.mpl_connect("key_press_event", handle_interaction)
    fig.canvas.mpl_connect("scroll_event", handle_interaction)
    
    print("\n[Viewer Active] Interactive window initialized successfully.")
    plt.show()

def main():
    # 💡 INTELLIGENT SMART SWITCH:
    # If the mask already exists, it skips the long AI wait time automatically.
    # If it is a new patient and the mask is missing, it runs the full AI loop!
    mask_path = os.path.join("results", "liver.nii.gz")
    
    if os.path.exists(input_path) and os.path.exists(mask_path):
        print("Existing patient files detected. Skipping computational AI wait time...")
    else:
        print("Initiating full pipeline processing...")
        print("Loading DICOM files from folder...")
        volume = load_dicom(folder_path)

        save_nifti(volume, input_path)
        print("NIfTI file created successfully!")

        print("Running high-accuracy liver segmentation...")
        mask_path = segment_liver(input_path)

    print("Preparing overlay arrays...")
    ct_volume = load_nifti(input_path)
    mask_volume = load_nifti(str(mask_path))

    visualize_overlay(ct_volume, mask_volume)

if __name__ == "__main__":
    main()
