"""This module provides liver segmentation using TotalSegmentator.
It receives an input NIfTI path and returns the generated liver-mask path."""

from pathlib import Path

from totalsegmentator.python_api import (
    totalsegmentator,
)


def segment_liver(
    input_path,
    output_directory="results",
):
    """
    Segment the liver from a CT NIfTI volume.

    Parameters
    ----------
    input_path : str or Path
        Path to the CT volume in NIfTI format.

    output_directory : str or Path, optional
        Directory where TotalSegmentator should save its output.

    Returns
    -------
    Path
        Path to the generated liver segmentation mask.

    Notes
    -----
    The full-resolution TotalSegmentator model is used rather than the
    lower-resolution fast mode.

    CPU execution is currently used to avoid GPU VRAM limitations on the
    development hardware.
    """

    input_path = Path(input_path)

    output_directory = Path(
        output_directory
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"Starting liver segmentation for: "
        f"{input_path.name}"
    )

    totalsegmentator(
        input=str(input_path),
        output=str(output_directory),
        fast=False,
        roi_subset=["liver"],
        device="cpu",
    )

    output_mask = (
        output_directory
        / "liver.nii.gz"
    )

    if not output_mask.exists():
        raise FileNotFoundError(
            "TotalSegmentator completed but "
            "liver.nii.gz was not found."
        )

    print(
        f"Liver segmentation completed: "
        f"{output_mask}"
    )

    return output_mask