<h1>LIVER DIGITAL TWIN: Functional Liver Planning</h1>
<blockquote>
    <p><strong>A Computational Medical Imaging &amp; Virtual Hepatectomy Framework for Quantitative Functional Assessment of the Liver</strong></p>
    <p><em>Undergraduate Graduation  Project — Medical Biophysics</em></p>
</blockquote>
<hr />

<h2> Summary &amp; Overview</h2>
<p>Surgical planning for liver resection (hepatectomy)  relies heavily on anatomical volume calculations. While measuring the prospective remnant liver volume  provides basic safety thresholds, anatomical volume does not always correlate linearly with functional hepatic reserve, especially in patients with underlying parenchymal diseases (e.g., steatosis, cirrhosis, or post-chemotherapy tissue changes).</p>

<p><strong>LIVER DIGITAL TWIN</strong> is an open-source computational biophysics pipeline designed to bridge the gap between anatomical structure and tissue quality. By integrating 3D Computed Tomography (CT) volume reconstruction, automated deep-learning segmentation, quantitative Hounsfield Unit (HU) radiomics, and simulated surgical resection, this framework constructs a patient-specific "Digital Twin" to estimate and visualize both the <strong>quantity</strong> and <strong>quality</strong> of functional liver tissue post-resection.</p>

<blockquote>
    <p><strong>Disclaimer:</strong> <em>This software is an educational and scientific research prototype developed as an undergraduate graduation thesis. It is not approved for clinical diagnostic or therapeutic use.</em></p>
</blockquote>
<hr />

<h2>Medical &amp; Scientific Motivation</h2>
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

<h2>Results and Visualization</h2>

<h3>Liver Segmentation</h3>
<p>The current pipeline implements an interactive 2D Axial Slice Overlay Viewer built on an optimized Matplotlib desktop window layout manager. The framework reads multi-dimensional NumPy arrays and applies a mathematical transparency layer to overlay the semi-transparent red AI tissue mask cleanly over the grayscale anatomical CT scan slices. It automatically tracks real-time array boundaries, enabling cross-sectional visual inspection via the mouse scroll wheel or keyboard arrow keys without masking underlying dense skeletal structures.</p>


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

  <tr>
    <td align="center"><strong>Create Environment</strong></td>
    <td>
      Create and activate a Conda environment using Python
      <strong>3.10–3.12</strong> (tested with <strong>3.10</strong>):
      <br>
      <code>conda create -n liver-twin python=3.10</code>
      <br>
      <code>conda activate liver-twin</code>
    </td>
  </tr>

  <tr>
    <td align="center"><strong>Install PyTorch</strong></td>
    <td>
      Install the <strong>PyTorch</strong> build appropriate for your system and available hardware acceleration.
    </td>
  </tr>

  <tr>
    <td align="center"><strong>Install Dependencies</strong></td>
    <td>
      Install the remaining project dependencies from <code>requirements.txt</code>:
      <br>
      <code>pip install -r requirements.txt</code>
    </td>
  </tr>

  <tr>
    <td align="center"><strong>Run Application</strong></td>
    <td>
      Launch the application from the project folder:
      <br>
      <code>python main.py</code>
    </td>
  </tr>
</table>

  

### TODOS
----------------
- [x] add more documentation to the code
- [x] in readme , for someone wanna reproduce this experiment and results 
    - [x] write exactly what he will do
    - [x] add requirements file (libs that should be installed to get this project working)
- [x] use conda for environment management (read about this)
- [x] add .gitignore (read about it)

- [x] make the workflow as follows :
    - user open the main window ---> he will find a button to load nii file ---->when click it will open file selection window----> select the file ---> the file open and the user can see the volume
    - user can maniplate ww and ww , and can go through slice with a slider 
- [x] add a button that call liver segmentation ( so that when click ) the total segmentator will run ---->output the liver mask -----> the mask overlayed over liver tissue ------> we cab see liver with generatedd mask
- [ ] afte we get this app that enable user to load his files and run segmentation ...we will stop and re-organize the project and add decide what to add more
