class MedicalVolume:         # telling python a new datatype called Medical volume
    def __init__(self, voxel_data, spacing, origin, direction, metadata=None):         #metadata = None, so that we can store any additional information about the volume, such as patient information, scan parameters, etc. 

        self.voxel_data = voxel_data
        self.spacing = spacing
        self.origin = origin
        self.direction = direction
        self.metadata = metadata
        self.segmentations={}   # Empty dictionaries mean: # we reserve places for fututre results
        self.features={}  #Empty dictionaries mean:"We don't have results yet, but modules can add them later."

#Now the object knows: the acutal ct values (voxel_data), the physical size(spacing), the location(origin), the orientation(direction)

            

 