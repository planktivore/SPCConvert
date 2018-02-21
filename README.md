# README #

SPCConvert - Raw ROIs to rendered mosaics and stats with a web application

### Overview ###

* SPCConvert is a collection of python scripts to convert raw region of interest (ROI) images from a real-time plankton camera such as the SPC into statistics and image mosaics.
* Version: 1.01a
* Authors: Paul L. D. Roberts, Eric Orenstein

### Quickstart ###

The fastest way to get your system setup is to install Anaconda and then add the opencv3 and pystache python modules through conda:

1. Install Anaconda for python 2.7 from https://anaconda.org/
2. Open a terminal and install the required python modules:
    * `$ conda install -c menpo opencv3`
    * `$ conda install -c conda-forge pystache`
    * `$ conda install -c conda-forge pandas`
3. Change to the SPCconvert directory and run it
    * `$ python spcconvert.py [path_to_image_dir]`

### Requirements ###
* python 2.7, numpy, scipy, skimage, opencv3, pystache, pandas
* Tested on mac, and windows

The requirements are also listed in requirements.txt file.

### settings.xml ###

Some of the basic processing steps can be configured by editing settings.xml. 

### Detailed Description ###

SPCconvert takes as input a directory or directory of directories of images and builds image mosaics and stats from these images.
It is designed to take as input images from real-time ROI detection systems such as the Scripps Plankton Camera (http://spc.ucsd.edu)
and build a web app that is similar to the image browsers from spc.ucsd.edu

The code collects all of the images in the directory, loads them into RAM and then splits the work of processing them over multiple
processes up to NCPU-1. The processing consists of:

1. color conversion
2. edge-detection and segmentation
3. morphological feature extraction
4. foreground masking
5. inverse filtering of masked foreground

The results are then saved into a new directory structure and a web app is build from the data using pystache (mustache) templates
and some javascript and html files stored in the app directory.

Additionally spreadsheet (features.tsv) is created with features of every detected object. These are vastly more 
detailed that those available in browser - especially intensity measurements can be found useful in further analyses
of the observed entities. 

### Configuring for a Specific Camera ###

There are a few settings that need to be adjusted to use with a different camera. The primary ones are:

1. BayerPattern: This needs to match your camera, for example BG is used for the SPC, SPCP cameras and RG is used for the SPC-BIG, UW, USC cameras
2. PixelSize: This is pixel size of pixels in object space in um/pixel of the given camera/lens combination, it is converted to mm/pixel in the code
    * SPC: 7.38 um/pixel (Sony ICX814, 3.69 um pixels with 0.5x objective)
    * SPCP: 0.62 um/pixel (Sony ICX834, 3.1 um pixels with 5x objective)
    * SPC2: 7.38 um/pixel (Sony ICX814, 3.69 um pixels with 0.5x objective)
    * SPCP2: 0.738 um/pixel (Sony ICX814, 3.69 um pixels with 5x objective)
    * SPC-PWSSC, NOAA: 22.6 um/pixel (Sony ICX834, 3.1 um pixels with 0.137x objective)
    * SPC-BIG, UW, USC: 25.18 um/pixel (Sony IMX253, 3.45 um pixels with 0.137x objective)

### Contribution guidelines ###

* Help is needed to improve this code. Specific areas are:

1. Improved control of processing and app building parameters via settings.xml
2. Managementr of cases with more images then can fit in RAM
3. Saving morpholical and color data to a deparate csv file
4. Handling bad images, images that are too large or small

* Contact Paul Roberts (plroberts@ucsd.edu) for information about contributing code, bugs, and all things SPC related.