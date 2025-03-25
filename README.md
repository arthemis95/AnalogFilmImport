# AnalogFilmImport
Small project to help me preprocess my film pictures once I get the scans from the lab.

It iterates over all subfolders in a specified directory, searches for .tif files, ensures they have a 32Bit float Colour depth, as this is the native format for Gimp . Then generates .jpg previews.

## Arguments
  - path : Relative or absolute path to the Folder containing your images. Required, first argument. 
  - \-\-quality : Quality setting for jpeg compression, if none is provided, it will be deduced automatically. (Binary search, performance intensive, but a nice option). Optional.
  - \-\-max_size : Maximum allowed size for .jpg files, in megabytes. Optional. Default is 10MB
