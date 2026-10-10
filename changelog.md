# Changelog

# Latest changes

# Added
- Segmentation of vessels, tumors and the 8 Couinaud segments.
- A Segmentation tab to choose what to run and what to display.
- Colored overlays in 2D and one 3D surface per structure.
- Structure registry in `core/structures.py`.

# Fixed
- Corrected voxel spacing order to prevent distortion in the 3D liver view.
- Corrected 2D aspect ratios for coronal and sagittal views.
- Repaired a corrupt TotalSegmentator config file that made every run fail.
- Reduced memory use while saving segmentation results.

# Changed
- Saved segmentation masks now load when the user clicks.
- Removed the duplicate slice slider from the Data tab; slice navigation remains in the pane header.