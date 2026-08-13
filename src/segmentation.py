import os
from pathlib import Path
def segment_liver(input_path):
    # This overrides nnUNet's internal data iterator background process loops
    os.environ["nnUNet_n_proc_DA"] = "0"
    os.environ["nnUNet_n_proc_preprocessing"] = "0"
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"

    from totalsegmentator.python_api import totalsegmentator

    output_folder = Path("results")
    output_folder.mkdir(exist_ok=True)

    print("\n--- Starting High-Accuracy CPU Liver Segmentation ---")
    print("This runs sequentially in a single process stream to protect system memory.")
    
    totalsegmentator(
        input=str(input_path),
        output=str(output_folder),            
        roi_subset=["liver"],   # Restricts matrix evaluation to only one organ
        device="cpu"            
    )

    output_mask = output_folder / "liver.nii.gz"
    return output_mask