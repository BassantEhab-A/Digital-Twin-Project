"""This module provides liver segmentation using TotalSegmentator.
It receives an input NIfTI path and returns the generated liver-mask path."""

from pathlib import Path

from totalsegmentator.python_api import totalsegmentator


def segment_liver(
    input_path,
    output_mask_path,
    device="cpu",
    fast=False,
):
    """
    Segment the liver from a CT NIfTI volume.

    Parameters
    ----------
    input_path : str or Path
        Path to the CT volume in NIfTI format.

    output_mask_path : str or Path
        Full path (including filename) where the liver mask should be saved.
        The parent directory is created automatically. TotalSegmentator
        itself writes '<output_dir>/liver.nii.gz'; this function renames
        that file to `output_mask_path` before returning.

    device : str, optional
        'cpu' or 'cuda'. CPU is used by default to avoid GPU VRAM limits.

    fast : bool, optional
        If True, uses the lower-resolution model. Defaults to False.

    Returns
    -------
    Path
        Path to the generated liver segmentation mask.
    """
    input_path = Path(input_path)
    output_mask_path = Path(output_mask_path)

    # TotalSegmentator writes everything into a directory.
    # We give it a dedicated temporary directory, then move the file.
    staging_directory = output_mask_path.parent / "_totalseg_staging"
    staging_directory.mkdir(parents=True, exist_ok=True)

    print(f"Starting liver segmentation for: {input_path.name}")

    totalsegmentator(
        input=str(input_path),
        output=str(staging_directory),
        fast=fast,
        roi_subset=["liver"],
        device=device,
    )

    # TotalSegmentator's naming convention: '<output>/liver.nii.gz'
    staged_mask = staging_directory / "liver.nii.gz"

    if not staged_mask.exists():
        raise FileNotFoundError(
            f"TotalSegmentator completed but {staged_mask} was not found."
        )

    # Move the mask to its final, case-specific destination.
    output_mask_path.parent.mkdir(parents=True, exist_ok=True)
    if output_mask_path.exists():
        output_mask_path.unlink()
    staged_mask.replace(output_mask_path)

    # Clean up the staging directory.
    try:
        staging_directory.rmdir()
    except OSError:
        # Not empty (extra files) — leave it, harmless.
        pass

    print(f"Liver segmentation completed: {output_mask_path}")
    return output_mask_path