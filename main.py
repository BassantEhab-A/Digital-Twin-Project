import os
import sys

os.environ["nnUNet_n_proc_DA"] = "0"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"


import matplotlib
matplotlib.use("QtAgg")  
import matplotlib.pyplot as plt
import numpy as np

from src.Image_Loader import load_dicom
from src.image_io import load_nifti, save_nifti
from src.segmentation import segment_liver

folder_path = r"C:\Users\Bassant\Downloads\3Dircadb1.2\PATIENT2_DICOM"

def visualize_overlay(ct_volume, mask_volume, patient_id):
    """Generates an interactive axial slice overlay viewer."""
    
    try:
        plt.switch_backend("QtAgg")
    except Exception:
        plt.switch_backend("TkAgg")  # Reliable native Windows fallback backend

    ct_data = ct_volume.voxel_data
    mask_data = mask_volume.voxel_data

    num_slices = ct_data.shape[0]
    current_slice = 0

    fig, ax = plt.subplots(figsize=(8, 8))
    fig.canvas.manager.set_window_title(f"Liver Digital Twin Workspace - [{patient_id}]")

    vmin, vmax = -100, 200 

    im_ct = ax.imshow(ct_data[current_slice, :, :], cmap="gray", vmin=vmin, vmax=vmax, origin="lower")  #takes a 2d slice of the 3d volume and displays it in grayscale   
    masked_liver = np.ma.masked_where(mask_data[current_slice, :, :] == 0, mask_data[current_slice, :, :])
    im_mask = ax.imshow(masked_liver, cmap="Reds", alpha=0.4, vmin=0, vmax=1, origin="lower")

    ax.set_title(f"Patient: {patient_id} | Slice {current_slice}/{num_slices - 1} | Use Scroll/Arrows")
    ax.axis("off")

    def update_slice():
        ax.set_title(f"Patient: {patient_id} | Slice {current_slice}/{num_slices - 1} | Use Scroll/Arrows")
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
   
    print(f"\n[Viewer Active] Interactive window initialized successfully for {patient_id}.")
    plt.show()

def main():
    print("Initializing Automated Patient Digital Twin Viewer")
    
    patient_id = "3Dircadb1.2"

    input_path = f"patient_{patient_id}.nii.gz"
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)
    mask_path = os.path.join(results_dir, f"liver_{patient_id}.nii.gz")

    print(f"\n[Active Patient Profile ID]: {patient_id}")
    print(f"Target Input Base Path: {input_path}")
    print(f"Target Mask Output Path: {mask_path}")
   
    if os.path.exists(input_path) and os.path.exists(mask_path):
        print("\nPre-compiled digital twin files detected for this patient case!")
        print("Bypassing computational AI segmentation. Initializing UI viewer...")
    else:
        # Cleaned up pipeline processing logic
        volume = load_dicom(folder_path)
        save_nifti(volume, input_path)
        calculated_mask = segment_liver(input_path)
        
        if os.path.exists(calculated_mask) and str(calculated_mask) != mask_path:
            os.replace(calculated_mask, mask_path)

    print("Preparing overlay visualization...")
    ct_volume = load_nifti(input_path)
    mask_volume = load_nifti(mask_path)

    visualize_overlay(ct_volume, mask_volume, patient_id)

if __name__ == "__main__":
    print("Matplotlib backend initialization:", plt.get_backend())   
    plt.switch_backend("QtAgg")   
    print("Matplotlib backend confirmed switch:", plt.get_backend())
    main()
