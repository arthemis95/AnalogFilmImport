__jpgxl_supported__ = False
import os
import glob
import subprocess
import argparse
import io
from multiprocessing import Pool
try:
    import pillow_jxl
    __jpgxl_supported__ = True
except ImportError:
    pass
from PIL import Image
from PIL import TiffImagePlugin
import numpy as np

#----------------------------------------------------------------------------------------------------------------
# Sometimes, with B/W images 16Bit TIFs mess up the jpg convert
# Enforcing 8Bit TIFs for JPG conversion
# Args:
#    image (PIL.Image): The input image to be processed.
# Returns
#    image (PIL.Image): The processed image
#
def tiff_force_8bit(image):
    if image.format == 'TIFF' and image.mode == 'I;16':
        array = np.array(image)
        normalized = (array.astype(np.uint16) - array.min()) * 255.0 / (array.max() - array.min())
        image = Image.fromarray(normalized.astype(np.uint8))

    return image

#----------------------------------------------------------------------------------------------------------------
# Deduces the optimal JPEG quality setting for a given image to ensure it meets a maximum file size constraint.
# Args:
#    image (PIL.Image): The input image to be processed.
#    max_size_bytes (int): The maximum allowed file size for the output JPEG image, in bytes.
# Returns:
#    int: Quality setting (hopefully) achieving desired size
#
def deduce_optimal_quality(image, max_size_bytes, fileEnding):
	
    max_quality = 100  # Maximum quality setting (0-100)
    min_quality = 10  # Minimum quality setting (0-100)
    mid_quality = None
    max_iter = 15
    prev_quality = 0
    fileEnding_ = fileEnding

    # Perform binary search to find the optimal quality
    while max_iter:
 
        # Create an in-memory file-like object
        buffer = io.BytesIO()

        # Determining next quality setting
        mid_quality = (min_quality + max_quality) // 2
        if mid_quality == prev_quality:
            return mid_quality

        max_iter -= 1

        # Save the image with the current quality setting to the in-memory buffer
        image.save(buffer, format=fileEnding_, quality=mid_quality, optimize=True)

        # Get the size of the in-memory buffer
        buffer_size = buffer.getbuffer().nbytes

        # Checking for acceptable quality
        if buffer_size >= max_size_bytes * 0.95 and buffer_size <=  max_size_bytes:
            return mid_quality

        # Adjust the search range based on the buffer size
        if buffer_size <= max_size_bytes:
            min_quality = mid_quality + 1
        else:
            max_quality = mid_quality - 1
        prev_quality = mid_quality
    # Return the min quality if no optimal quality is found
    return min_quality

#----------------------------------------------------------------------------------------------------------------
# Processes a single image file by converting it to 16-bit depth, compressing it, and saving it as a JPEG file.
#
#    Args:
#        file (str): The path to the input image file.
#
def process_image(argument):

    # Unpacking args
    file, quality, max_size, jpgxl = argument
    fileEnding = 'jxl' if jpgxl else 'jpg'
    print('Processing {}'.format(os.path.basename(file)))

    # Open the image using PIL, doing this before 16-bit conversion, to avoid downconverting again
    im = Image.open(file)

    # Remove the STRIPOFFSETS tag from the EXIF data to avoid issues with JPEG/JPGXL compression
    exif = im.getexif()
    del exif[TiffImagePlugin.STRIPOFFSETS]

    # Generate the output JPEG file path
    newpath = file.rstrip('.tif') + '.' + fileEnding
    
    if not jpgxl:
        # updating the fileEnding for JPEG
        fileEnding = 'JPEG'

	#Enforcing 8 bit image, required by jpg
    im = tiff_force_8bit(im)

    # Determine the optimal JPEG quality setting based on the maximum allowed file size
    if quality is None:
        quality = deduce_optimal_quality(im, max_size * 1000 * 1000, fileEnding)

    # Save the image as a JPEG file with the determined quality setting
    im.save(newpath, fileEnding, quality=quality)
	
	# Convert the image to 32-bit float and compress it using ZIP compression
    executable = ""
    if os.path.exists("/usr/bin/magick"):
        executable = "magick"
    elif os.path.exists("/usr/bin/convert"):
        executable = "convert"
    else:
        print("Magick needs to be installed for TIF conversion")
        raise Exception

    subprocess.run([executable, file, '-depth', '32', '-define', 'quantum:format=floating-point', '-compress', 'ZIP', file])


if __name__ == '__main__':
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Preparing images for processing.')
    parser.add_argument('path', help='Path to the project folder')
    parser.add_argument('--quality', help='Quality setting for jpeg compression, if none is provided, it will be deduced automatically.', default=None, required=False, type=int)
    parser.add_argument('--max_size', help='Maximum allowed size for .jpg files, in megabytes', default=10, required=False, type=int)
    parser.add_argument('--jpgxl', help='Use JPEG-XL instead of JPEG for compression', default=False, required=False, action='store_true')
    args = parser.parse_args() 
    
    if args.jpgxl and not __jpgxl_supported__:
        print("JPEG-XL is not supported, falling back to JPEG")
        args.jpgxl = False
    
    # Find all TIFF files in the specified project folder
    files = []
    for root, _, files_ in os.walk(args.path):
            for file in files_:
                if file.endswith(".tif"):
                    files.append(os.path.join(root,file))

    arguments = []
    for file in files:
        arguments.append((file, args.quality, args.max_size, args.jpgxl))
	
    # Create a multiprocessing Pool to process images in parallel
    with Pool(os.cpu_count()) as p:
        p.map(process_image, arguments)
