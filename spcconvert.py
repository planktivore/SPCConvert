# -*- coding: utf-8 -*-
"""
spcconvert - batch conversion and webpage building for SPC images


"""

import cvtools
import cv2
import os
import sys
import glob
import time
import datetime
import json
import shutil
import math
from multiprocessing import Pool, Process, Queue
from threading import Thread
import multiprocessing
from itertools import repeat
from operator import itemgetter
from pytz import timezone
import pystache
import numpy as np
import xmlsettings
from scipy import stats



flow_frames = True

class Counter(object):
    def __init__(self):
        self.val = multiprocessing.Value('i', 0)

    def increment(self, n=1):
        with self.val.get_lock():
            self.val.value += n

    @property
    def value(self):
        return self.val.value

def process_image(bundle):

    image_path = bundle['image_path']
    image = bundle['image']
    data_path = bundle['data_path']
    image_dir = bundle['image_dir']
    cfg = bundle['cfg']
    total_images = bundle['total_images']

    filename = os.path.basename(image_path)

    # Patch bug in PCAM where timestamp string is somtimes incorrectly set to
    # 0 or a small value. Use the file creation time instead.
    #
    # This is okay so long as the queue in PCAM mostly empty. We can adapt
    # the frame counter to fix this in the future.

    timestamp = 0
    for substr in filename.split('-'):
        try:
            timestamp = int(substr)
            break;
        except ValueError:
            pass
            
    # Range check the timestamp
    if timestamp < 100000:
        print "" + filename + " strange timestamp."
        #timestamp = os.path.getctime(image_path)
        output = {}
        return output

    prefix = filename.split('.')[0]
    # image is preloaded so no need to load here
    #image = cvtools.import_image(data_path,filename,bayer_pattern=cv2.COLOR_BAYER_BG2RGB)
    img_c_8bit = cvtools.convert_to_8bit(image)

    # images will be saved out later so set save_to_disk to False
    features = cvtools.quick_features(
        img_c_8bit,
        save_to_disk=False,
        abs_path=image_dir,
        file_prefix=prefix,
        cfg=cfg
    )
    use_jpeg = use_jpeg = cfg.get("UseJpeg").lower() == 'true'
    if use_jpeg:
        filename = os.path.basename(image_path).split('.')[0] + '.jpeg'
    else:
        filename = os.path.basename(image_path).split('.')[0] + '.png'

    # handle new file formwat with unixtime in microseconds
    if timestamp > 1498093400000000:
        timestamp = timestamp/1000000
        
    # Range check the timestamp
    if timestamp < 100000 or timestamp > time.time():
        print "" + filename + " strange timestamp."
        #timestamp = os.path.getctime(image_path)
        output = {}
        return output

    
    # print "Timestamp: " + str(timestamp)
    
    timestring = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    entry = {}
    entry['maj_axis_len'] = features['major_axis_length']
    entry['min_axis_len'] = features['minor_axis_length']
    entry['aspect_ratio'] = features['aspect_ratio']
    entry['area'] = features['area']
    entry['clipped_fraction'] = features['clipped_fraction']
    entry['orientation'] = features['orientation']*180/math.pi
    entry['timestring'] = timestring
    entry['timestamp'] = timestamp
    entry['width'] = img_c_8bit.shape[1]
    entry['height'] = img_c_8bit.shape[0]
    entry['url'] = bundle['reldir'] + '/' + filename
    entry['file_size'] = os.path.getsize(image_path)

    output = {}
    output['entry'] = entry
    output['image_path'] = image_dir
    output['prefix'] = prefix
    output['features'] = features

    return output

# threaded function for each process to call
# queues are used to sync processes
def process_bundle_list(bundle_queue,output_queue):

    while True:
        try:
            output_queue.put(process_image(bundle_queue.get()))
        except:
            time.sleep(0.02*np.random.rand())
# Split a list into sublists
def chunks(l, n):
    n = max(1, n)
    return [l[i:i+n] for i in xrange(0, len(l), n)]

# Process a directory of images
def run(data_path,cfg):

    print "Running SPC image conversion..."

    # get the base name of the directory
    base_dir_name = os.path.basename(os.path.abspath(data_path))

    # list the directory for tif images
    print "Listing directory " + base_dir_name + "..."

    image_list = []
    if cfg.get('MergeSubDirs',"false").lower() == "true":
        sub_directory_list = sorted(glob.glob(os.path.join(data_path,"[0-9]"*10)))
        for sub_directory in sub_directory_list:
            print "Listing sub directory " + sub_directory + "..."
            image_list += glob.glob(os.path.join(sub_directory,"*.tif"))
    else:
        image_list += glob.glob(os.path.join(data_path,"*.tif"))
    
    image_list = sorted(image_list)

    # skip if no images were found
    if len(image_list) == 0:
        print "No images were found. skipping this directory."
        return

    # Get the total number of images in the directory
    total_images = len(image_list)

    # Create the output directories for the images and web app files
    subdir = os.path.join(data_path,'..',base_dir_name + '_static_html')
    if not os.path.exists(subdir):
        os.makedirs(subdir)
    image_dir = os.path.join(subdir,'images')
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)

    print "Starting image conversion and page generation..."

    # loop over the images and do the processing
    images_per_dir = cfg.get('ImagesPerDir',2000)
    
    if cfg.get("BayerPattern").lower() == "rg":
        bayer_conv = cv2.COLOR_BAYER_RG2RGB
    if cfg.get("BayerPattern").lower() == "bg":
        bayer_conv = cv2.COLOR_BAYER_BG2RGB

    print "Loading images...\r",
    bundle_queue = Queue()
    for index, image in enumerate(image_list):

        reldir = 'images/' + str(images_per_dir*int(index/images_per_dir)).zfill(5)
        absdir = os.path.join(image_dir,str(images_per_dir*int(index/images_per_dir)).zfill(5))

        filename = os.path.basename(image)

        if not os.path.exists(absdir):
            os.makedirs(absdir)

        bundle = {}
        bundle['image_path'] = image
        bundle['image'] = cvtools.import_image(os.path.dirname(image),filename,bayer_pattern=bayer_conv)
        bundle['data_path'] = data_path
        bundle['image_dir'] = absdir
        bundle['reldir'] = reldir
        bundle['cfg'] = cfg
        bundle['total_images'] = total_images

        bundle_queue.put(bundle)
        print "Loading images... (" + str(index) + " of " + str(total_images) + ")\r",

        #if index > 2000:
        #    total_images = index
        #    break

    # Get the number o proceess to use based on CPUs
    n_threads = multiprocessing.cpu_count() - 1
    if n_threads < 1:
        n_threads = 1

    # Create the set of processes and start them
    start_time = time.time()
    output_queue = Queue()
    processes = []
    for i in range(0,n_threads):
        p = Process(target=process_bundle_list, args=(bundle_queue,output_queue))
        p.start()
        processes.append(p)

    # Monitor processing of the images and save processed images to disk as they become available
    print "\nProcessing Images...\r",
    counter = 0
    entry_list = []
    use_jpeg = use_jpeg = cfg.get("UseJpeg").lower() == 'true'
    raw_color = cfg.get("SaveRawColor").lower() == 'true'
    while True:
        print "Processing and saving images... (" + str(counter).zfill(5) + " of " + str(total_images).zfill(5) + ")\r",

        if counter >= total_images:
            break

        #if output_queue.qsize() == 0:

        try:
            output = output_queue.get()
            if output:
                entry_list.append(output['entry'])
                output_path = os.path.join(output['image_path'],output['prefix'])
                if use_jpeg:
                    if raw_color:
                        cv2.imwrite(os.path.join(output_path+"_rawcolor.jpeg"),output['features']['rawcolor'])
                    cv2.imwrite(os.path.join(output_path+".jpeg"),output['features']['image'])
                else:
                    if raw_color:
                        cv2.imwrite(os.path.join(output_path+"_rawcolor.png"),output['features']['rawcolor'])
                    cv2.imwrite(os.path.join(output_path+".png"),output['features']['image'])
                
                cv2.imwrite(os.path.join(output_path+"_binary.png"),output['features']['binary'])
            
            counter = counter + 1
        except:
            time.sleep(0.05)

    # Record the total time for processing
    proc_time = int(math.floor(time.time()-start_time))

    # Terminate the processes in case they are stuck
    for p in processes:
        p.terminate()

    print "\nPostprocessing..."

    # sort the entries by height and build the output
    entry_list.sort(key=itemgetter('maj_axis_len'),reverse=True)

    # Create histograms of several key features

    # image resolution in mm/pixel
    image_res = cfg.get('PixelSize',22.1)/1000;
    
    #print "Image resolution is set to: " + str(image_res) + " mm/pixel."

    # Get arrays from the dict of features
    total_images = len(entry_list)
    nbins = int(np.ceil(np.sqrt(total_images)))
    maj_len = np.array(map(itemgetter('maj_axis_len'),entry_list))*image_res
    min_len = np.array(map(itemgetter('min_axis_len'),entry_list))*image_res
    aspect_ratio = np.array(map(itemgetter('aspect_ratio'),entry_list))
    orientation = np.array(map(itemgetter('orientation'),entry_list))
    area = np.array(map(itemgetter('area'),entry_list))*image_res*image_res
    unixtime = np.array(map(itemgetter('timestamp'),entry_list))
    elapsed_seconds = unixtime - np.min(unixtime)
    file_size = np.array(map(itemgetter('file_size'),entry_list))/1000.0

    #print unixtime
    
    total_seconds = max(elapsed_seconds)
    print "Total seconds recorded: " + str(total_seconds)
    if total_seconds < 1:
        total_seconds = 1
        
    print "\nComputing histograms..."

    # Compute histograms
    all_hists = {}
    hist = np.histogram(area,nbins)
    all_hists['area'] = json.dumps(zip(hist[1].tolist(),hist[0].tolist()))
    hist = np.histogram(maj_len,nbins)
    all_hists['major_axis_length'] = json.dumps(zip(hist[1].tolist(),hist[0].tolist()))
    hist = np.histogram(min_len,nbins)
    all_hists['minor_axis_length'] = json.dumps(zip(hist[1].tolist(),hist[0].tolist()))
    hist = np.histogram(aspect_ratio,nbins)
    all_hists['aspect_ratio'] = json.dumps(zip(hist[1].tolist(),hist[0].tolist()))
    hist = np.histogram(elapsed_seconds,np.uint32(total_seconds))
    all_hists['elapsed_seconds'] = json.dumps(zip(hist[1].tolist(),hist[0].tolist()))
    hist = np.histogram(orientation,nbins)
    all_hists['orientation'] = json.dumps(zip(hist[1].tolist(),hist[0].tolist()))
    hist = np.histogram(file_size,nbins)
    
    print "\nComputing stats..."

    all_hists['file_size'] = json.dumps(zip(hist[1].tolist(),hist[0].tolist()))
    # Compute general stats from features
    all_stats = {}
    all_stats['area'] = stats.describe(area)
    all_stats['major_axis_length'] = stats.describe(maj_len)
    all_stats['minor_axis_length'] = stats.describe(min_len)
    all_stats['aspect_ratio'] = stats.describe(aspect_ratio)
    all_stats['elapsed_seconds'] = stats.describe(elapsed_seconds)
    all_stats['orientation'] = stats.describe(orientation)
    all_stats['file_size'] = stats.describe(file_size)


    print "Building web app..."

    # Load html template for rendering
    template = ""
    with open(os.path.join('app','index.html'),"r") as fconv:
        template = fconv.read()

    # Define the render context from the processed histograms, images, and stats
    context = {}
    context['version'] = '1.0.1.05'
    context['total_images'] = total_images
    context['proc_time'] = proc_time
    context['duration'] = total_seconds
    context['compression_ratio'] = int((1000.0*24*total_images)/np.sum(file_size))
    context['rois_per_second'] = total_images/context['duration']
    context['kb_per_second'] = int(np.sum(file_size)/context['duration'])
    context['recording_started'] = datetime.datetime.fromtimestamp(np.min(unixtime)).strftime('%Y-%m-%d %H:%M:%S')
    context['app_title'] = "SPC Convert: " + base_dir_name
    context['dir_name'] = base_dir_name
    context['raw_color'] = raw_color
    context['image_res'] = image_res
    if use_jpeg:
        context['image_ext'] = '.jpeg'
    else:
        context['image_ext'] = '.png'
    context['stats_names'] = [{"name":"Min"},{"name":"Max"},{"name":"Mean"},{"name":"Standard Deviation"},{"name":"Skewness"},{"name":"Kurtosis"}]

        # definie the charts to display from the histogram data
    charts = []
    for chart_name, data_values in all_hists.iteritems():
        chart = {}
        chart['source'] = 'js/' + chart_name + '.js'
        chart['name'] = chart_name
        units = ""
        if chart_name == 'area':
            units = " (mm*mm)"
        if chart_name == 'major_axis_length' or chart_name == 'minor_axis_length':
            units = " (mm)"
        if chart_name == 'file_size':
            units = " (kB)"
        if chart_name == 'elapsed_seconds':
            units = " (s)"
        if chart_name == 'orientation':
            units = " (deg)"
        chart['title'] = 'Histogram of ' + chart_name + units
        chart['x_title'] = chart_name + units
        chart['y_title'] = 'counts'
        chart['stats_title'] = chart_name
        chart['data'] = data_values
        chart['stats'] = []
        chart['stats'].append({"name":"Min","value":"{:10.3f}".format(all_stats[chart_name][1][0])})
        chart['stats'].append({"name":"Max","value":"{:10.3f}".format(all_stats[chart_name][1][1])})
        chart['stats'].append({"name":"Mean","value":"{:10.3f}".format(all_stats[chart_name][2])})
        chart['stats'].append({"name":"Standard Deviation","value":"{:10.3f}".format(math.sqrt(all_stats[chart_name][3]))})
        chart['stats'].append({"name":"Skewness","value":"{:10.3f}".format(all_stats[chart_name][4])})
        chart['stats'].append({"name":"Kurtosis","value":"{:10.3f}".format(all_stats[chart_name][5])})
        charts.append(chart)

    context['charts'] = charts
    
    # render the html page and save to disk
    page = pystache.render(template,context)

    with open(os.path.join(subdir,'spcdata.html'),"w") as fconv:
        fconv.write(page)

    # remove any old app files and try to copy over new ones
    try:
        shutil.rmtree(os.path.join(subdir,"css"),ignore_errors=True)
        shutil.copytree("app/css",os.path.join(subdir,"css"))
        shutil.rmtree(os.path.join(subdir,"js"),ignore_errors=True)
        shutil.copytree("app/js",os.path.join(subdir,"js"))
    except:
        print "Error copying supporting files for html."

    # Load roistore.js database for rendering
    template = ""
    with open(os.path.join('app','js','database-template.js'),"r") as fconv:
        template = fconv.read()

    context = {}
    context['image_items'] = entry_list
    context['table'] = base_dir_name

    # render the javascript page and save to disk
    page = pystache.render(template,context)

    with open(os.path.join(subdir,'js','database.js'),"w") as fconv:
        fconv.write(page)

    print "Done."
    
def valid_image_dir(test_path):

    list = glob.glob(os.path.join(test_path,"*.tif"))
    
    if len(list) > 0:
        return True
    else:  
        return False
    
    
# Module multiprocessing is organized differently in Python 3.4+
try:
    # Python 3.4+
    if sys.platform.startswith('win'):
        import multiprocessing.popen_spawn_win32 as forking
    else:
        import multiprocessing.popen_fork as forking
except ImportError:
    import multiprocessing.forking as forking

if sys.platform.startswith('win'):
    # First define a modified version of Popen.
    class _Popen(forking.Popen):
        def __init__(self, *args, **kw):
            if hasattr(sys, 'frozen'):
                # We have to set original _MEIPASS2 value from sys._MEIPASS
                # to get --onefile mode working.
                os.putenv('_MEIPASS2', sys._MEIPASS)
            try:
                super(_Popen, self).__init__(*args, **kw)
            finally:
                if hasattr(sys, 'frozen'):
                    # On some platforms (e.g. AIX) 'os.unsetenv()' is not
                    # available. In those cases we cannot delete the variable
                    # but only set it to the empty string. The bootloader
                    # can handle this case.
                    if hasattr(os, 'unsetenv'):
                        os.unsetenv('_MEIPASS2')
                    else:
                        os.putenv('_MEIPASS2', '')

    # Second override 'Popen' class with our modified version.
    forking.Popen = _Popen

if __name__ == '__main__':

    multiprocessing.freeze_support()

    if len(sys.argv) <= 1:
        print "Please input a dirtectory of data directories, aborting."
    else:
        if len(sys.argv) <= 2:

            # load the config file
            cfg = xmlsettings.XMLSettings(os.path.join(sys.path[0],'settings.xml'))

            combine_subdirs = cfg.get('MergeSubDirs',"False").lower() == "true"
            
            print "Settings file: " + os.path.join(sys.path[0],'settings.xml')
            
            # If given directory is a single data directory, just process it
            if valid_image_dir(sys.argv[1]):
                run(sys.argv[1],cfg)
                sys.exit(0)

            # Otherwise look for data directories in the given directory

            # List data directories and process each one
            # expect the directories to be in the unixtime format
            directory_list = sorted(glob.glob(os.path.join(sys.argv[1],"[0-9]"*10)))

            if len(directory_list) == 0:
                print "No data directories found."
                sys.exit(0)
                


            # Process the data directories in order
            print 'Processing each data directory...'
            for directory in directory_list:
                if os.path.isdir(directory):
                    if not combine_subdirs:
                        if valid_image_dir(directory):
                            run(directory,cfg)
                    else:
                        run(directory,cfg)

