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

image_res = 22.0/1000

fullImageSize = [2824,4240]

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
            

    
    # use the file creation time if the timestamp is funky
    if timestamp < 100000:
        timestamp = os.path.getctime(image_path)

    prefix = filename.split('.')[0]
    # image is preloaded so no need to load here
    #image = cvtools.import_image(data_path,filename,bayer_pattern=cv2.COLOR_BAYER_BG2RGB)
    img_c_8bit = cvtools.convert_to_8bit(image)
    
    # images will be saved out later so set save_to_disk to False
    features = cvtools.quick_features(
        img_c_8bit,
        save_to_disk=False,
        abs_path=image_dir,
        file_prefix=prefix
    )

    filename = os.path.basename(image_path).split('.')[0] + '.png'

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

    while bundle_queue.qsize() > 0:
        output_queue.put(process_image(bundle_queue.get()))

# Split a list into sublists
def chunks(l, n):
    n = max(1, n)
    return [l[i:i+n] for i in xrange(0, len(l), n)]

# Process a directory of images
def run(data_path,cfg):

    # get the base name of the directory
    base_dir_name = os.path.basename(data_path)

    # list the directory for tif images
    print "Listing directory " + base_dir_name + "..."
    image_list = sorted(glob.glob(os.path.join(data_path,"*.tif")))
    
    # skip if no images were found
    if len(image_list) == 0:
        print "No images were found. skipping this directory."
        return

    # Get the total number of images in the directory
    total_images = len(image_list)

    # Create the output directories for the images and web app files
    subdir = os.path.join(data_path,'..',base_dir_name + '_flowframes')
    if not os.path.exists(subdir):
        os.makedirs(subdir)
    image_dir = os.path.join(subdir,'images')
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)

    print "Starting image conversion and page generation..."

    # loop over the images and do the processing
    images_per_dir = 2000

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
        bundle['image'] = cvtools.import_image(data_path,filename,bayer_pattern=cv2.COLOR_BAYER_BG2RGB)
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
    n_threads = 1
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
    raw_image = np.zeros((fullImageSize[0],fullImageSize[1],3))
    image_index = 0
    while True:
        print "Processing and saving images... (" + str(counter).zfill(5) + " of " + str(total_images).zfill(5) + "), " + str(bundle_queue.qsize()).zfill(5)+ " images queued.\r",
        
        if counter >= total_images:
            break
        
        if output_queue.qsize() == 0:
            time.sleep(0.05)   
        else:
            output = output_queue.get()
            fileprefix = output['entry']['url'].split('.')[0]

            # EXAMPLE SPC-NOAA-1363060960-000097-264-0-784-168-152
            roi_index = int(fileprefix.split('-')[-6])
            roi_x = int(fileprefix.split('-')[-4])
            roi_y = int(fileprefix.split('-')[-3])
            roi_w = int(fileprefix.split('-')[-2])
            roi_h = int(fileprefix.split('-')[-1])

            if roi_index == image_index:
                raw_image[roi_y:(roi_y+roi_h):1,roi_x:(roi_x+roi_w):1,:] = output['features']['image']
            else:
                output_path = os.path.join(output['image_path'],'frame_'+str(image_index).zfill(5))
                cv2.imwrite(os.path.join(output_path+".tif"),raw_image)
                raw_image = 0*raw_image
                image_index = roi_index
                raw_image[roi_y:(roi_y+roi_h):1,roi_x:(roi_x+roi_w):1,:] = output['features']['image']
                
            counter = counter + 1
        
    # Record the total time for processing
    proc_time = int(math.floor(time.time()-start_time))
    
    # Terminate the processes in case they are stuck
    for p in processes:
        p.terminate()
    
    print "Done."

if __name__ == '__main__':

    if len(sys.argv) <= 1:
        print "Please input a dirtectory of data directories, aborting."
    else:
        if len(sys.argv) <= 2:
        
            # load the config file
            cfg = xmlsettings.XMLSettings(os.path.join(sys.path[0],'settings.xml'))

            # If given directory is a single data directory, just process it
            if os.path.isfile(os.path.join(sys.argv[1],'config.xml')):
                run(sys.argv[1],cfg)
                exit()

            # Otherwise look for data directories in the given directory

            # List data directories and process each one
            # expect the directories to be in the unixtime format
            directory_list = sorted(glob.glob(os.path.join(sys.argv[1],"[0-9]"*10)))
            
            if len(directory_list) == 0:
                print "No data directories found."
                exit()
                
            # Process the daata directories in order
            for directory in directory_list:
                if os.path.isdir(directory):
                    if os.path.isfile(os.path.join(directory,'config.xml')):
                        run(directory,cfg)
