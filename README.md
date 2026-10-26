<h1>LIVER DIGITAL TWIN: Functional Liver Planning</h1>
<blockquote>
    <p><strong>A Computational Medical Imaging & Virtual Hepatectomy Framework for Quantitative Functional Assessment of the Liver</strong></p>
    <p><em>Undergraduate Graduation  Project — Medical Biophysics</em></p>
</blockquote>
<hr />

<h2> Summary & Overview</h2>
<p>Surgical planning for liver resection (hepatectomy)  relies heavily on anatomical volume calculations. While measuring the prospective remnant liver volume  provides basic safety thresholds, anatomical volume does not always correlate linearly with functional hepatic reserve, especially in patients with underlying parenchymal diseases (e.g., steatosis, cirrhosis, or post-chemotherapy tissue changes).</p>

<p><strong>LIVER DIGITAL TWIN</strong> is an open-source computational biophysics pipeline designed to bridge the gap between anatomical structure and tissue quality. By integrating 3D Computed Tomography (CT) volume reconstruction, automated deep-learning segmentation, quantitative Hounsfield Unit (HU) radiomics, and simulated surgical resection, this framework constructs a patient-specific "Digital Twin" to estimate and visualize both the <strong>quantity</strong> and <strong>quality</strong> of functional liver tissue post-resection.</p>

## Our Strategy
- We will first build a complete working pipeline and treat it as our MVP, then iterate on it with the help of surgeons — our end users — so improvements are driven by experts.

- We want an app where the user can load an abdominal CT volume, run liver segmentation (including the 8 Couinaud segments and vessels), followed by tumor segmentation, so all these structures are visible. Then, in a separate view, the user can interactively place a cutting plane and, after each action, see the volume of the remnant part and whether it is safe for the patient.

- Once the pipeline is complete, we will focus on publishing this work in a paper, then continue improving it.

<blockquote>
    <p><strong>Disclaimer:</strong> <em>This software is an educational and scientific research prototype developed as an undergraduate graduation thesis. It is not approved for clinical diagnostic or therapeutic use.</em></p>
</blockquote>
<hr />

<h2>Medical & Scientific Motivation</h2>
<p>When a surgeon evaluates a patient for major liver resection, two critical questions must be answered:</p>
<ol>
    <li><strong>How much liver volume will remain after surgery?</strong></li>
    <li><strong>Is the remaining tissue healthy enough to sustain metabolic function?</strong></li>
</ol>
<p>Standard surgical workflows rely on manual or semi-automated contouring to estimate remnant volume. However, tissue heterogeneity, fatty infiltration, and regional vascular perfusion differences remain unquantified.</p>
<p>This project implements a <strong>Digital Twin methodology</strong> in a medical imaging context:</p>
<ul>
    <li><strong>Anatomical Modeling:</strong> Reconstructing physical 3D patient geometry directly from DICOM coordinate spaces.</li>
    <li><strong>Tissue Characterization:</strong> Quantifying parenchymal health through Hounsfield Unit (HU) mapping and radiomic texture features.</li>
    <li><strong>Virtual Intervention:</strong> Simulating virtual resections to evaluate post-surgical outcomes in a risk-free computational environment.</li>
</ul>
<hr />

<h2>Current Progress</h2>

<ul>
  <li>Loading CT volumes from NIfTI files</li>
  <li>Loading DICOM CT series (recursive folder discovery)</li>
  <li>2D slice navigation (Axial, Coronal, Sagittal) with synchronized crosshair</li>
  <li>Window Width / Window Level adjustment</li>
  <li>TotalSegmentator integration for:
    <ul>
      <li>Liver</li>
      <li>Hepatic vessels, portal &amp; splenic vein, inferior vena cava</li>
      <li>Liver tumors</li>
      <li>8 Couinaud segments</li>
    </ul>
  </li>
  <li>Colored 2D mask overlays and one 3D surface per structure</li>
  <li>Saved masks are loaded from disk on demand (no unnecessary recomputation)</li>
  <li>Resection simulation tab:
    <ul>
      <li>Planar cuts (axial / coronal / sagittal, adjustable position and keep-side)</li>
      <li>Anatomical cuts by Couinaud segment</li>
      <li>Manual cuts through three picked points</li>
      <li>Automatic cut suggestions around the tumor + safety margin</li>
      <li>Remnant volume, future liver remnant (FLR), and safety threshold</li>
      <li>Vascular impact analysis: severed branches, ischemic / congested territory, effective FLR</li>
    </ul>
  </li>
</ul>

<h3>Results</h3>

https://github.com/user-attachments/assets/44afeebf-0320-49b2-a0c8-dbb6f0b47c96

<h2>Architecture</h2>

<p>Every module has one job. Processing (segmentation, resection maths) is kept independent of the GUI so it can be tested and reused.</p>

<pre>
Image loading       →  CaseManager.ct_volume
Segmentation        →  SegmentationWorker (Qt thread) → CaseManager.masks
Display             →  _display_masks() (adds derived overlays) → QuadViewer
Resection           →  ResectionEngine.simulate() → ResectionResult → ResectionTab
</pre>

<ul>
  <li><strong><code>src/io</code></strong> — DICOM and NIfTI readers/writers; produce and consume <code>MedicalVolume</code>.</li>
  <li><strong><code>src/core/medical_volume.py</code></strong> — geometry holder: voxel ⇄ world conversion, spacing in <code>(x, y, z)</code> mm, array indexed <code>(z, y, x)</code>.</li>
  <li><strong><code>src/core/structures.py</code></strong> — the single source of truth for every structure: key, label, color, TotalSegmentator task, draw order. Adding a structure means one line here.</li>
  <li><strong><code>src/core/case_manager.py</code></strong> — per-case state and results paths; never modifies masks.</li>
  <li><strong><code>src/core/resection/</code></strong> — pure numpy/scipy/scikit-image, <em>no Qt</em>:
    <ul>
      <li><code>cuts.py</code> — <code>PlaneCut</code>, <code>SegmentCut</code>, and two automatic suggesters.</li>
      <li><code>engine.py</code> — <code>ResectionEngine.simulate()</code>: volumes, margin check, FLR, safety.</li>
      <li><code>vessels.py</code> — <code>VesselTree</code>: skeleton graph, portal/hepatic labelling, devascularized territory after a cut.</li>
      <li><code>margin.py</code> — anisotropic Euclidean distance helpers.</li>
      <li><code>result.py</code> — frozen <code>ResectionResult</code> dataclass.</li>
    </ul>
  </li>
  <li><strong><code>src/segmentation_module/</code></strong> — TotalSegmentator wrapper + background <code>SegmentationWorker</code>.</li>
  <li><strong><code>src/gui/</code></strong> — Qt widgets only: tabs, viewers, main window. No medical maths lives here.</li>
</ul>

<h2>Project Directory Tree</h2>
<p>As managed inside the repository environment, processing operations are fully decoupled from local visualization tools to prevent system dependency pollution:</p>

<pre>
Liver-Digital-Twin/
<pre>
Liver-Digital-Twin/
│
├── main.py                                  # Application entry point
├── README.md
├── requirements.txt                         # Python dependencies
├── .gitignore                               # Files Git should not track
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/                                # Domain model
│   │   ├── __init__.py
│   │   ├── case_manager.py                  # Per-case state + result paths
│   │   ├── medical_volume.py                # MedicalVolume + geometry
│   │   ├── structures.py                    # Structure registry
│   │   └── resection/                       # Pure resection maths (no Qt)
│   │       ├── __init__.py
│   │       ├── cuts.py                      # PlaneCut, SegmentCut, suggesters
│   │       ├── engine.py                    # ResectionEngine.simulate
│   │       ├── margin.py                    # Distance / dilation helpers
│   │       ├── result.py                    # ResectionResult
│   │       └── vessels.py                   # VesselTree + vascular impact
│   │
│   ├── gui/                                 # Qt user interface
│   │   ├── __init__.py
│   │   ├── main_window.py                   # Main window + controller logic
│   │   ├── tabs/
│   │   │   ├── __init__.py
│   │   │   ├── data_tab.py                  # Data tab
│   │   │   ├── segmentation_tab.py          # Segmentation tab
│   │   │   ├── resection_tab.py             # Resection tab
│   │   │   └── scrollable.py                # Vertical-scroll wrapper
│   │   └── viewer/
│   │       ├── __init__.py
│   │       ├── pane_header.py               # Colored orientation bar + slider
│   │       ├── slice_viewer.py              # Single 2D slice pane
│   │       ├── viewer_3d.py                 # PyVista 3D viewer
│   │       └── quad_viewer.py               # 2×2 layout orchestrator
│   │
│   ├── io/                                  # Medical image readers/writers
│   │   ├── __init__.py
│   │   ├── dicom_io.py                      # DICOM series loading
│   │   └── nifti_io.py                      # NIfTI load/save
│   │
│   └── segmentation_module/                 # Liver segmentation pipeline
│       ├── __init__.py
│       ├── segmentation.py                  # TotalSegmentator wrapper
│       └── segmentation_runner.py           # QThread worker
│
├── results/                                 # Per-case outputs (gitignored)
│   └── <case_name>/
│       ├── input_<case>.nii.gz              # DICOM→NIfTI conversion
│       └── liver.nii.gz                     # Segmentation mask
│
└── docs/
    ├── screenshots/
    ├── architecture.md
    └── resection.md
</pre>
</pre>

<h2>Project Download & Environment Setup</h2>

<table>
  <tr>
    <td align="center"><strong>Get the Code</strong></td>
    <td>
      Clone the repository using Git or download it as a ZIP from GitHub:
      <br>
      <code>git clone https://github.com/BassantEhab-A/Digital-Twin-Project.git</code>
      <br>
      Then open a terminal inside the project folder.
    </td>
  </tr>

### TODOS

----------------------
## Step 1 — Upload & CT Viewer

- [x] Set up a basic project repository on GitHub.
- [x] Build a simple frontend upload button for CT scans (DICOM or NIfTI format).
- [x] Display the 2D slices (Axial, Coronal, Sagittal views) so the user can scroll through the scan.

### 🧠 Learning Points for Step 1:
- **Git & Version Control:** Learn how to initialize a repository (`git init`), make clean commits (`git add`, `git commit`), and push your code to GitHub (`git push`). Always write clear commit messages like `feat: add CT file upload component`.
- **Software Engineering Planning:** Learn how to break down a big idea into a tiny, working piece (MVP). Don't try to build everything at once; start by just getting a file to upload and display.
- **Understanding DICOMs & Metadata:** Learn how medical images are stored. Unlike standard JPEGs, DICOM files contain metadata headers (voxel spacing, patient orientation, slice thickness) that tell software how pixels map to real-world millimeters.

---

## Step 2 — One-Click Segmentation Backend

- [X] Connect a backend endpoint that takes the uploaded CT scan.
- [X] Run TotalSegmentator in the background to automatically extract masks for:
  * [X] Liver
  * [X] Tumors (if present)
  * [X] Vascular structures & Couinaud segments
- [X] Return the resulting binary masks back to the frontend.

### 🧠 Learning Points for Step 2:
- **What is Image Segmentation?:** Learn the core computer vision concept of classification vs. segmentation—teaching a computer to label every single pixel or voxel as "liver", "tumor", or "background".
- **How TotalSegmentator Works:** Learn about the **nnU-Net** framework. Understand how the model was trained on diverse clinical data using 3D U-Net encoder-decoder architectures with skip connections, and how it handles inference using patch-based processing to fit within GPU memory limits.
- **Project Structure & API Design:** Learn how to design a clean client-server architecture where the frontend handles user interaction and the backend handles heavy AI processing.

---

## Step 3 — 3D Rendering & Marching Cubes

- [X] Convert the voxel masks generated by the AI into smooth 3D surfaces.
- [X] Render the liver, tumor, and vessels together in an interactive 3D viewer (rotate, zoom, change transparency).

### 🧠 Learning Points for Step 3:
- **Voxel Masks vs. Meshes:** Understand the difference between 3D voxel grids (like digital Lego blocks) and smooth vector **meshes** (made of vertices, edges, and triangles).
- **Mask-to-Mesh Conversion (Marching Cubes):** Learn how the **Marching Cubes** algorithm scans a 3D binary mask and generates a continuous triangle surface so it looks smooth and realistic.
- **Basic Mesh Operations:** Learn about mesh cleanup, such as smoothing (removing jagged staircase artifacts from pixels) and decimation (reducing triangle count so the 3D app runs fast).

---

## Step 4 — Interactive Plane Cut & Safety Check

- [X] Add a UI slider to place a cutting plane through the 3D liver model.
- [X] Implement a cutting script that slices the liver volume along that plane (planar, anatomical, and manual modes).
- [X] Calculate the **Remnant Liver Volume** (percentage of liver left behind) and display a safety warning if it falls below the adjustable clinical threshold (default 30 %).
- [X] Additional: tumor margin coverage, future liver remnant (FLR) excluding tumor, and vascular impact analysis (ischemic / congested territory, effective FLR).

### 🧠 Learning Points for Step 4:
- **Git Branching & Merging:** Learn how to use feature branches (`git checkout -b feature/cutting-plane`), resolve merge conflicts, and merge your work safely back into the main branch.
- **Geometric Slicing & Boolean Operations:** Learn how software performs mathematical cuts on 3D meshes and voxel volumes.
- **Clinical Safety Logic:** Understand how engineers translate real-world medical rules (like avoiding post-operative liver failure) into simple, automated code checks.

---
<h2>Running the Tests</h2>

<p>The resection and vascular analysis modules are pure Python and fully unit-tested (no GUI or GPU required):</p>

<pre>
pip install pytest
pytest test_resection.py test_vessels.py -v
</pre>

<p>Test coverage includes: world/voxel round-trip with rotated direction, anisotropic volume calculation, plane-cut geometry, tumor margin dilation and distance, segment suggestions, vessel tree labelling, downstream ischemia / congestion, and effective FLR.</p>

## 🚀 What's Next?
Once this MVP is fully working and tested, you can move on to phase two: adding advanced vascular graphs, automated Couinaud segment coloring, and uncertainty quantification!