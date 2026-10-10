class MedicalVolume:         # telling python a new datatype called Medical volume
    """A 3D medical image.
 
      * voxel_data : numpy array indexed (Z, Y, X)   [SimpleITK array order]
      * spacing    : tuple in (X, Y, Z) order        [SimpleITK GetSpacing order]
      * origin     : (X, Y, Z)
      * direction  : flattened 3x3 matrix
 
    Use `spacing_xyz` / `spacing_zyx` instead of indexing `spacing` by hand.
    """
    def __init__(self, voxel_data, spacing, origin, direction, metadata=None):         #metadata = None, so that we can store any additional information about the volume, such as patient information, scan parameters, etc. 

        self.voxel_data = voxel_data
        self.spacing = spacing
        self.origin = origin
        self.direction = direction
        self.metadata = metadata
        self.segmentations={}   # Empty dictionaries mean: # we reserve places for fututre results
        self.features={}  #Empty dictionaries mean:"We don't have results yet, but modules can add them later."

    @property
    def spacing_xyz(self):
        return self.spacing
 
    @property
    def spacing_zyx(self):
        """Spacing in the same order as voxel_data axes."""
        return self.spacing[::-1]

 