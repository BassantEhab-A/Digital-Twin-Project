# Main graphical interface for the Liver Digital Twin.


from pathlib import Path

from PySide6.QtCore import (Qt,)

from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)


from src.Image_Loader import (load_dicom,)

from src.gui.segmentation_worker import (SegmentationWorker,)

from src.image_io import (load_nifti,save_nifti,)




class MainWindow(QMainWindow):
    """
    Main desktop window for the Liver Digital Twin application.


    The window coordinates loading, visualization, interaction, and
    segmentation while keeping the underlying medical-image algorithms
    inside dedicated backend modules.
    """


    def __init__(self):
        """Initialize application state and construct the interface."""


        super().__init__()


    # Current case state
       
        self.ct_volume = None
        self.liver_mask = None


        # Type of source loaded by the user:
        # "nifti" or "dicom".
        self.current_source_type = None


        # Path of the original NIfTI file or DICOM directory.
        self.current_source_path = None


        # Stable identifier used to separate patient/case results.
        self.current_case_id = None


        # NIfTI file supplied to TotalSegmentator.
        # For NIfTI input this is the original file.
        # For DICOM input it is created internally.
        self.segmentation_input_path = None


        # Keep references to the worker/thread while segmentation runs.
        self.segmentation_thread = None
        self.segmentation_worker = None


        self._configure_window()
        self._build_ui()


 # Application construction


    def _configure_window(self):
        """Configure the top-level application window."""


        self.setWindowTitle("Liver Digital Twin")


        self.resize(1200,800,)


        self.setStatusBar(QStatusBar())


        self.statusBar().showMessage("Ready - Load medical imaging data.")


    def _build_ui(self):
        """Build the control panel and medical-image viewer."""


        central_widget = QWidget()


        self.setCentralWidget(central_widget)


        main_layout = QHBoxLayout(central_widget)


        control_panel = (self._create_control_panel())


        main_layout.addWidget(control_panel,1,)


        main_layout.addWidget(self.viewer,4,)




# Patient data


        data_group = QGroupBox("Patient Data")
        data_layout = QVBoxLayout(data_group)
        self.load_nifti_button = QPushButton("Load NIfTI")

        self.load_nifti_button.clicked.connect(self.load_nifti_file)
        self.load_dicom_button = QPushButton("Load DICOM Folder")
        self.load_dicom_button.clicked.connect(self.load_dicom_folder)
        data_layout.addWidget(self.load_nifti_button)
        data_layout.addWidget(self.load_dicom_button)


# Slice navigation


        slice_group = QGroupBox("Slice Navigation")
        slice_layout = QVBoxLayout(slice_group)

        self.slice_label = QLabel("Slice: -")

        self.slice_slider = QSlider(Qt.Horizontal)

        slice_layout.addWidget(self.slice_label)
        slice_layout.addWidget(self.slice_slider)


        # Liver segmentation


        segmentation_group = QGroupBox("Liver Segmentation")

        segmentation_layout = QVBoxLayout(segmentation_group)
        self.segment_button = QPushButton("Segment Liver")

        self.segment_button.clicked.connect(self.start_liver_segmentation)
        segmentation_layout.addWidget(self.segment_button)




    #  volume handling


    def _set_current_volume( self,volume,):
   


        self.ct_volume = volume


        self.liver_mask = None


        self.viewer.set_volume( volume )
        number_of_slices = (self.ct_volume.voxel_data.shape[0])


        middle_slice = (number_of_slices // 2)


        self.slice_slider.setRange(0,number_of_slices - 1,)


       
    # Existing segmentation reuse


    # Slice and window controls
   
    # Segmentation preparation



    # Segmentation


   



