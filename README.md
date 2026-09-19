<h1>LIVER DIGITAL TWIN: Functional Liver Planning</h1>
<blockquote>
    <p><strong>A Computational Medical Imaging & Virtual Hepatectomy Framework for Quantitative Functional Assessment of the Liver</strong></p>
    <p><em>Undergraduate Graduation  Project — Medical Biophysics</em></p>
</blockquote>
<hr />

<h2> Summary & Overview</h2>
<p>Surgical planning for liver resection (hepatectomy)  relies heavily on anatomical volume calculations. While measuring the prospective remnant liver volume  provides basic safety thresholds, anatomical volume does not always correlate linearly with functional hepatic reserve, especially in patients with underlying parenchymal diseases (e.g., steatosis, cirrhosis, or post-chemotherapy tissue changes).</p>

<p><strong>LIVER DIGITAL TWIN</strong> is an open-source computational biophysics pipeline designed to bridge the gap between anatomical structure and tissue quality. By integrating 3D Computed Tomography (CT) volume reconstruction, automated deep-learning segmentation, quantitative Hounsfield Unit (HU) radiomics, and simulated surgical resection, this framework constructs a patient-specific "Digital Twin" to estimate and visualize both the <strong>quantity</strong> and <strong>quality</strong> of functional liver tissue post-resection.</p>

## Our srategy :
- we will first make a complete working pipeline and consider this as our MVP the we will go through iterating through it to improve with the help  of surgoans - our end users - and make our imporovemtns driven by experts.

- we want an app where the user can upload a ct volume for abdomen and can run liver segmentation (including liver 8 segments and vessels) followed with tumor segmentation so he can see all these parts segmented. Then in another window he can interactively run a plane cutting where after each action he can see the volume of remananet part and weither this is safe to patient or not .

- once we have a complete pipeline we will first focus on puplishing this work in a paper then we can go through improving it 

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
  <li>Loading DICOM CT series</li>
  <li>CT slice navigation</li>
  <li>Window Width / Window Level adjustment</li>
  <li>Liver segmentation using TotalSegmentator</li>
  <li>Liver mask overlay on the CT volume</li>
</ul>

<h3>Results</h3>

https://github.com/user-attachments/assets/44afeebf-0320-49b2-a0c8-dbb6f0b47c96

<h2>Project Directory Tree</h2>
<p>As managed inside the repository environment, processing operations are fully decoupled from local visualization tools to prevent system dependency pollution:</p>

<pre>
Liver-Digital-Twin/
Liver-Digital-Twin/
│
├── main.py
├── README.md
├── requirements.txt
│   └── Required Python libraries
├── .gitignore
│   └── Files Git should not track
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── case_manager.py
│   │   └── medical_volume.py
│   ├── gui/
│   │   ├── main_window.py
│   │   └── volume_viewer.py
│   ├── io/
│   │   ├── __init__.py
│   │   ├── dicom_io.py
│   │   └── nifti_io.py
│   └── segmentation_module
│       ├── segmentation_runner.py
│       └── segmentation.py
├── results/
└── docs/
    └── project screenshots
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

### [ ] Step 1 — Upload & CT Viewer

- [ ] Build a simple frontend upload button for CT scans (DICOM or NIfTI format).
- [ ] Display the 2D slices (Axial, Coronal, Sagittal views) so the user can scroll through the scan.

- **Learning/Tech Focus:** Understanding how to parse medical volume metadata (spacing and dimensions).

### [ ] Step 2 — One-Click Segmentation Backend

- [ ] Connect a backend endpoint that takes the uploaded CT, runs TotalSegmentator in the background, and extracts masks for:
  * Liver
  * Tumors (if present)
  * Vascular structures & Couinaud segments

- **Deliverable:** The app successfully returns segmented binary masks.

### [ ] Step 3 — 3D Rendering & Marching Cubes

- [ ] Convert the voxel masks into smooth 3D surfaces using the **Marching Cubes** algorithm.
- [ ] Render the liver, tumor, and vessels together in a 3D interactive viewer (rotate, zoom, toggle transparency).

- **Deliverable:** A clear 3D digital twin of the patient's liver visible in the browser.

### [ ] Step 4 — Interactive Plane Cut & Safety Check

- [ ] Add a simple UI slider or handle to place a cutting plane through the 3D liver model.
- [ ] **The Safety Logic (The "Dangerous or Not?" Check):**
  * Cut the liver mesh and voxel volume along that plane.
  * Calculate the **Remnant Liver Volume** (percentage of liver left behind).
  * *Clinical Rule of Thumb:* If the remnant volume drops below roughly **25–30%** (for a healthy liver), flag it as **High Risk / Dangerous** (risk of post-operative liver failure).

- **Deliverable:** Interactive cut simulation with a real-time safety warning message.
