```markdown
# LIVER DIGITAL TWIN: Functional Liver Planning

> **A Computational Medical Imaging & Virtual Hepatectomy Framework for Quantitative Functional Assessment of the Liver**
>
> *Undergraduate Graduation Thesis Project — Medical Biophysics*

---

## Executive Summary & Overview

Surgical planning for liver resection (hepatectomy) historically relies heavily on anatomical volume calculations. While measuring the prospective remnant liver volume (RLV) provides basic safety thresholds, anatomical volume does not always correlate linearly with functional hepatic reserve, especially in patients with underlying parenchymal diseases (e.g., steatosis, cirrhosis, or post-chemotherapy tissue changes).

**LIVER DIGITAL TWIN** is an open-source computational biophysics pipeline designed to bridge the gap between anatomical structure and tissue quality. By integrating 3D Computed Tomography (CT) volume reconstruction, automated deep-learning segmentation, quantitative Hounsfield Unit (HU) radiomics, and simulated surgical resection, this framework constructs a patient-specific "Digital Twin" to estimate and visualize both the **quantity** and **quality** of functional liver tissue post-resection.

> **Disclaimer:** *This software is an educational and scientific research prototype developed as an undergraduate graduation thesis. It is not approved for clinical diagnostic or therapeutic use.*

---

## Medical & Scientific Motivation

When a surgeon evaluates a patient for major liver resection, two critical questions must be answered:
1. **How much liver volume will remain after surgery?**
2. **Is the remaining tissue healthy enough to sustain metabolic function?**

Standard surgical workflows rely on manual or semi-automated contouring to estimate remnant volume. However, tissue heterogeneity, fatty infiltration, and regional vascular perfusion differences remain unquantified. 

This project implements a **Digital Twin methodology** in a medical imaging context:
* **Anatomical Modeling:** Reconstructing physical 3D patient geometry directly from DICOM coordinate spaces.
* **Tissue Characterization:** Quantifying parenchymal health through Hounsfield Unit (HU) mapping and radiomic texture features.
* **Virtual Intervention:** Simulating virtual resections to evaluate post-surgical outcomes in a risk-free computational environment.

---

## Results and Visualization

### Liver Segmentation

The current pipeline can display an axial CT slice together with the generated liver segmentation mask, allowing the segmentation to be visually inspected across the volume.

![Liver segmentation overlay](docs/images/liver_segmentation_overlay.png)

### Digital Twin Visualization

The project also includes a custom visualization environment for inspecting the segmented liver in multiple anatomical views and displaying quantitative information such as liver volume.

![Digital Twin visualization](docs/images/digital_twin_viewer.png)

---

## Core System Architecture & Workflow

The pipeline follows a modular **"Load → Segment → Resect → Report"** architecture, enforcing a strict Separation of Concerns (SoC) between file I/O, mathematical transformations, AI inference, and graphical rendering.

```text
+------------------+
| DICOM CT Series  |
+------------------+
         |
         v
+-----------------------------------------------------------+
| src/Image_Loader.py                                       |
| - Parse DICOM headers & slice order along Z-axis          |
+-----------------------------------------------------------+
         |
         v
+-----------------------------------------------------------+
| src/medical_volume.py (MedicalVolume Object)              |
| - Spacing (mm) | Origin (mm) | Direction Matrix | Voxels |
+-----------------------------------------------------------+
         |
         +----------------------------+
         |                            |
         v                            v
+-------------------+        +------------------------------+
| src/image_io.py   |        | src/segmentation.py          |
| - NIfTI I/O       |        | - TotalSegmentator (3D U-Net)|
+-------------------+        +------------------------------+
                                      |
                                      v
                             +------------------------------+
                             | Liver Mask & Vessel Graphs    |
                             +------------------------------+
                                      |
                                      v
                             +------------------------------+
                             | Virtual Resection / Radiomics|
                             +------------------------------+
                                      |
                                      v
                             +------------------------------+
                             | src/visualization/           |
                             | - 2D Cross-Section (Matplotlib)|
                             | - 4-Pane Workstation (PyVista)|
                             +------------------------------+

```

---

## Project Directory Tree

```text
Liver-Digital-Twin/
├── main.py                          # Application entry point, runtime router, and hardware guards
├── debug_check.py                   # Environment verification script
├── README.md                        # Project documentation
├── data/                            # Raw DICOM slices / NIfTI volumes (e.g., 3Dircadb1.1)
├── docs/
│   └── images/                      # Pipeline figures and UI visualization assets
│       ├── liver_segmentation_overlay.png
│       └── digital_twin_viewer.png
└── src/
    ├── medical_volume.py            # Core MedicalVolume class pairing voxel matrices with metadata
    ├── Image_Loader.py              # SimpleITK-based ingestion layer for DICOM directory sorting
    ├── image_io.py                  # Optimized NIfTI (.nii.gz) read/write interface
    ├── segmentation.py             # AI inference wrapper for TotalSegmentator (nnUNet)
    └── visualization/
        ├── slice_viewer_2d.py       # Interactive Matplotlib slice navigation with mask overlays
        └── slicer_dashboard.py      # Hardware-accelerated multi-pane VTK/PyVista workstation

```

### Core Data Structure: `MedicalVolume`

To avoid direct dependency on file-specific libraries (like PyDICOM or NiBabel) downstream, all volume data is converted into a standard `MedicalVolume` object encapsulating physical spatial geometry:

* **`voxel_data`**: 3D NumPy matrix representing CT tissue attenuation in Hounsfield Units.
* **`spacing`**: Physical voxel dimensions (dx, dy, dz) in millimeters.
* **`origin`**: 3D scanner coordinate origin (x0, y0, z0) in millimeters.
* **`direction`**: 3x3 direction cosine matrix orienting the image grid in patient physical space.

---

## Key Systems Engineering Problems & Solutions

Developing a high-performance 3D medical processing workstation on resource-constrained academic hardware required solving several low-level memory, graphics, and spatial indexing challenges.

### 1. Silent Termination & Out of Memory (OOM) Crashes

* **Issue:** Launching deep-learning segmentation models on host machines with 8 GB RAM caused immediate, silent Python process termination without a stack trace.
* **Cause:** TotalSegmentator and PyTorch load large compiled C++/CUDA binary backends into memory, instantly exceeding available physical RAM.


### 2. Multi-Process Execution Locks (`WinError 1455`)

* **Issue:** Terminal execution failed with `OSError: [WinError 1455] The paging file is too small for this operation to complete` during data augmentation.


### 3. Headless Graphics Engine Blockers (`FigureCanvasAgg`)

* **Issue:** GUI windows failed to launch during interactive visualization tasks, throwing warnings that `FigureCanvasAgg is non-interactive`.

### 4. Asymmetric Spatial Grid Discrepancies (Coordinate Permutations)

* **Issue:** Loading 3D spatial grids into PyVista resulted in empty or stretched coronal and sagittal view panes.
* **Cause:** Medical imaging libraries (e.g., SimpleITK) utilize C-style row-major array storage (Z, Y, X), whereas computer graphics engines (VTK/PyVista) expect column-major (X, Y, Z) memory ordering. Passing un-transposed arrays with anisotropic slice thickness (129 slices x 512 pixels) placed cut-planes outside geometric bounds.


### 5. Surface Mesh Reconstruction: Jagged Artifacts vs. Organ Shrinkage

* **Issue:** Generating 3D surfaces directly from discrete slice stacks created stair-step voxel artifacts along the vertical axis due to slice thickness spacing (1.6 mm). Standard Laplacian mesh smoothing caused severe surface contraction, underestimating total liver volume.


## Dataset & Technical Validation

The system is developed and validated using the **3Dircadb1.1** (3D Image Reconstruction for Comparison of Algorithm Database) patient dataset, containing abdominal CT volumes and expert manual ground-truth segmentations.

---

## Tech Stack & Dependencies

* **Language:** Python 3.10+
* **Core Scientific Computing:** NumPy, SciPy
* **Medical Image Handling:** SimpleITK, NiBabel, PyDICOM
* **AI & Segmentation:** PyTorch, TotalSegmentator (3D nnUNet architecture)
* **Visualization Engine:** Matplotlib (2D slicing), PyVista / VTK (Hardware-accelerated multi-pane workstation)
* **Medical Inspection Tools:** 3D Slicer

---

## Installation & Usage

### Prerequisites

* Anaconda / Miniconda package manager
* Dedicated Windows Paging File configuration (≥ 16 GB) if running on system environments with ≤ 8 GB physical RAM.

### Setup Environment

```bash
# Clone the project repository
git clone [https://github.com/your-username/liver-digital-twin.git](https://github.com/your-username/liver-digital-twin.git)
cd liver-digital-twin

# Create and activate conda environment
conda create -n liver_twin python=3.10 -y
conda activate liver_twin

# Install core dependencies
pip install numpy nibabel SimpleITK matplotlib pyvista PyQt5 total-segmentator

```

### Execution

Run the system via `main.py`:

```bash
python main.py

```

---

## Development Roadmap & Status

* [x] Layered Modular Software Architecture
* [x] Unified `MedicalVolume` Spatial Representation
* [x] SimpleITK DICOM Directory & Z-Coordinate Sorting
* [x] NIfTI File Format I/O
* [x] Deep Learning Liver Segmentation (TotalSegmentator)
* [x] Interactive 2D Cross-Sectional Slice Viewer
* [x] Hardware-Accelerated Multi-Pane PyVista Workstation
* [ ] Quantitative Dice Coefficient Validation vs. Ground-Truth
* [ ] Parenchymal Tissue Analysis (HU Stratification)
* [ ] Vascular Tree Extraction & Graph Representation
* [ ] Virtual Resection / Simulated Hepatectomy Engine
* [ ] Radiomics Feature Extraction (PyRadiomics Integration)
* [ ] Functional Liver Reserve Score Calculation

