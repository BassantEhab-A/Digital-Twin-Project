from pathlib import Path
from totalsegmentator.python_api import totalsegmentator

def segment_liver(input_path):
    output_folder = Path("results")
    output_folder.mkdir(exist_ok=True)

    print("Starting liver segmentation...")   # high accuracy segmentation without fast=True 
    #this to tell me what's going on and know at which step we are at , feedback is useful because TotalSegmentator can take significant time, especially on CPU.
    # this tells me that the segmentation process will startso I can monitor its progress and know when it's done.
    totalsegmentator(
        input=str(input_path),
        output=str(output_folder),
        fast=False,            #  use the normal/full-resolution model rather than the lower-resolution fast model.
        roi_subset=["liver"],
        device="cpu"           # FORCES CPU so the graphics card memory doesn't crash, avoid GPU VRAM limitations on our hardware.
    )

    output_mask = output_folder / "liver.nii.gz"
    return output_mask

    # I changed fast=False and device="cpu" to use the 32GB virtual RAM safety net

