# -*- coding: utf-8 -*-
"""
cvtools - image processing tools for plankton images

a simplified version for color conversion and database indexing only

"""
import time
import json
import os
import sys
import glob
import datetime
import pickle
import random, string
from math import pi
import cv2
from skimage import morphology, measure, exposure, restoration
from skimage import transform
from skimage.feature import register_translation
from skimage.filters import threshold_otsu, scharr, gaussian
import numpy as np
from scipy import ndimage
import xmlsettings

def make_gaussian(size, fwhm = 3, center=None):
    """ Make a square gaussian kernel.
    size is the length of a side of the square
    fwhm is full-width-half-maximum, which
    can be thought of as an effective radius.
    """

    x = np.arange(0, size, 1, float)
    y = x[:,np.newaxis]

    if center is None:
        x0 = y0 = size // 2
    else:
        x0 = center[0]
        y0 = center[1]

    output = np.exp(-4*np.log(2) * ((x-x0)**2 + (y-y0)**2) / fwhm**2)
    output = output/np.sum(output)

    return output

# import raw image
def import_image(abs_path,filename,raw=True,bayer_pattern=cv2.COLOR_BAYER_RG2RGB):

    # Load and convert image as needed
    img_c = cv2.imread(os.path.join(abs_path,filename),cv2.IMREAD_UNCHANGED)
    if raw:
        img_c = cv2.cvtColor(img_c,bayer_pattern)

    return img_c

# convert image to 8 bit with or without autoscaling
def convert_to_8bit(img,auto_scale=True):

    # Convert to 8 bit and autoscale
    if auto_scale:

        # result = np.float32(img)-np.median(img)
        # max_val1 = np.max(img)
        # max_val2 = np.max(result)
        # result[result < 0] = 0
        # result = result/(0.5*max_val1+0.5*max_val2)
        #
        # bch = result[:,:,0]
        # gch = result[:,:,1]
        # rch = result[:,:,2]
        # b_avg = np.mean(bch)
        # g_avg = np.mean(gch)
        # r_avg = np.mean(rch)
        # avg = np.mean(np.array([b_avg,g_avg,r_avg]))
        # #print "R: " + str(r_avg) + ", G: " + str(g_avg) + ", B: " + str(b_avg)
        # bch = bch*1.075
        # rch = rch*0.975
        # gch = gch*0.95
        # # bch = bch*avg/b_avg
        # # rch = rch*avg/r_avg
        # # gch = gch*avg/g_avg
        # # b_avg = np.mean(bch)
        # # g_avg = np.mean(gch)
        # # r_avg = np.mean(rch)
        # #print "New R: " + str(r_avg) + ", G: " + str(g_avg) + ", B: " + str(b_avg)
        # result[:,:,0] = bch
        # result[:,:,1] = gch
        # result[:,:,2] = rch

        #result = result/np.max(result)

        result = np.float32(img)-np.min(img)
        result[result<0.0] = 0.0
        if np.max(img) != 0:
            result = result/np.max(img)

        img_8bit = np.uint8(255*result)
    else:
        img_8bit = np.unit8(img)

    return img_8bit


def intensity_features(img, obj_mask):
    res = {}

    # assume that obj_mask contains one connected component
    prop = measure.regionprops(obj_mask.astype(np.uint8), img)[0]
    res["mean_intensity"] = prop.mean_intensity
    res["median_intensity"] = np.median(prop.intensity_image[prop.image])

    # invariant_intensity_moments = prop.weighted_moments_normalized
    # StdIntensity ^
    # MeanIntensityEdge
    # MassDisplacement
    # LowerQuartileIntensity
    # UpperQuartileIntensity
    # MADIntensity?
    return res

# extract simple features and create a binary representation of the image
def quick_features(img,save_to_disk=False,abs_path='',file_prefix='',cfg = []):
    """
    :param img: 8-bit array
    """
    # Pull out some settings from cfg if available
    if cfg:
        min_obj_area = cfg.get('MinObjectArea',100)
        objs_per_roi = cfg.get('ObjectsPerROI',1)
        deconv = cfg.get("Deconvolve").lower() == 'true'
        edge_thresh = cfg.get('EdgeThreshold',2.5)
        use_jpeg = cfg.get("UseJpeg").lower() == 'true'
        raw_color = cfg.get("SaveRawColor").lower() == 'true'
    else:
        min_obj_area = 100
        objs_per_roi = 1
        deconv = False
        use_jpeg = False
        raw_color = True
        edge_thresh = 2.5

    # Define an empty dictionary to hold all features
    features = {}

    features['rawcolor'] = np.copy(img)
    # compute features from gray image
    gray = np.uint8(np.mean(img,2))

    # threshold-based segmentation
    #med_val = np.median(gray)
    #std_val = np.std(gray)
    #thresh1 = threshold_otsu(gray)
    #thresh3 = med_val + 1.6*std_val
    #binary = (gray >= thresh1) | (gray >= thresh3)
    #bw_img1 = morphology.closing(binary,morphology.square(3))

    # edge-based segmentation
    edges_mag = scharr(gray)
    edges_med = np.median(edges_mag)
    edges_thresh = edge_thresh*edges_med
    edges = edges_mag >= edges_thresh
    edges = morphology.closing(edges,morphology.square(3))
    filled_edges = ndimage.binary_fill_holes(edges)
    edges = morphology.erosion(filled_edges,morphology.square(3))
    #edges = morphology.erosion(edges,morphology.square(3))

    # combine threshold and edge based segmentations
    bw_img2 = edges
    #bw_img = np.pad(bw_img2,1, 'constant')
    bw_img = bw_img2

    # Compute morphological descriptors
    label_img = morphology.label(bw_img,neighbors=8,background=0)
    props = measure.regionprops(label_img,gray)

    # clear bw_img
    bw_img = 0*bw_img

    props = sorted(props, reverse=True, key=lambda k: k.area)

    if len(props) > 0:

        # Init mask with the largest area object in the roi
        bw_img = (label_img)== props[0].label
        bw_img_all = bw_img.copy()

        base_area = props[0].area

        # use only the features from the object with the largest area
        max_area = 0
        max_area_ind = 0
        avg_area = 0.0
        avg_maj = 0.0
        avg_min = 0.0
        avg_or = 0.0
        avg_count = 0

        if len(props) > objs_per_roi:
            n_objs = objs_per_roi
        else:
            n_objs = len(props)

        for f in range(0,n_objs):

            if props[f].area > min_obj_area:
                bw_img_all = bw_img_all + ((label_img)== props[f].label)
                avg_count = avg_count + 1

            if f >= objs_per_roi:
                break

        # Take the largest object area as the roi area
        # no average
        avg_area = props[0].area
        avg_maj = props[0].major_axis_length
        avg_min = props[0].minor_axis_length
        avg_or = props[0].orientation
        avg_eccentricity = props[0].eccentricity
        avg_solidity = props[0].solidity

        # Calculate only for largest
        features_intensity = intensity_features(gray, bw_img)
        for k, v in features_intensity.items():
            features["gray_" + k] = v

        features_intensity = intensity_features(img[::, ::, 0], bw_img)
        for k, v in features_intensity.items():
            features["red_" + k] = v

        features_intensity = intensity_features(img[::, ::, 1], bw_img)
        for k, v in features_intensity.items():
            features["green_" + k] = v

        features_intensity = intensity_features(img[::, ::, 2], bw_img)
        for k, v in features_intensity.items():
            features["blue_" + k] = v

        # Check for clipped image
        if np.max(bw_img_all) == 0:
            bw = bw_img_all
        else:
            bw = bw_img_all/np.max(bw_img_all)

        clip_frac = float(np.sum(bw[:,1]) +
                np.sum(bw[:,-2]) +
                np.sum(bw[1,:]) +
                np.sum(bw[-2,:]))/(2*bw.shape[0]+2*bw.shape[1])
        features['clipped_fraction'] = clip_frac

        # Save simple features of the object
        features['area'] = avg_area
        features['minor_axis_length'] = avg_min
        features['major_axis_length'] = avg_maj
        if avg_maj == 0:
            features['aspect_ratio'] = 1
        else:
            features['aspect_ratio'] = avg_min/avg_maj
        features['orientation'] = avg_or
        features['eccentricity'] = avg_eccentricity
        features['solidity'] = avg_solidity
        #
        #

        # print "Foreground Objects: " + str(avg_count)

    else:

        features['clipped_fraction'] = 0.0

        # Save simple features of the object
        features['area'] = 0.0
        features['minor_axis_length'] = 0.0
        features['major_axis_length'] = 0.0
        features['aspect_ratio'] = 1
        features['orientation'] = 0.0
        features['eccentricity'] = 0
        features['solidity'] = 0

    # Masked background with Gaussian smoothing, image sharpening, and
    # reduction of chromatic aberration

    # mask the raw image with smoothed foreground mask
    blurd_bw_img = gaussian(bw_img_all,3)
    img[:,:,0] = img[:,:,0]*blurd_bw_img
    img[:,:,1] = img[:,:,1]*blurd_bw_img
    img[:,:,2] = img[:,:,2]*blurd_bw_img

    # Make a guess of the PSF for sharpening
    psf = make_gaussian(5, 3, center=None)

    # sharpen each color channel and then reconbine


    if np.max(img) == 0:
        img = np.float32(img)
    else:
        img = np.float32(img)/np.max(img)

    if deconv:

        img[img == 0] = 0.0001
        img[:,:,0] = restoration.richardson_lucy(img[:,:,0], psf, 7)
        img[:,:,1] = restoration.richardson_lucy(img[:,:,1], psf, 7)
        img[:,:,2] = restoration.richardson_lucy(img[:,:,2], psf, 7)

    # Estimate color channel shifts and try to align.
    # this works for most images but some still retain and offset.
    # need to figure out why...
    # r_shift, r_error, r_diffphase = register_translation(img[:,:,1], img[:,:,2],1)
    # b_shift, b_error, b_diffphase = register_translation(img[:,:,1], img[:,:,0],1)

    # # this swap of values is needed for some reason
    # if r_shift[0] < 0 and r_shift[1] < 0:
       # r_shift = -r_shift

    # if b_shift[0] < 0 and b_shift[1] < 0:
       # b_shift = -b_shift

    # r_tform = transform.SimilarityTransform(scale=1,rotation=0,translation=r_shift)
    # img[:,:,2] = transform.warp(img[:,:,2],r_tform)

    # b_tform = transform.SimilarityTransform(scale=1,rotation=0,translation=b_shift)
    # img[:,:,0] = transform.warp(img[:,:,0],b_tform)

    # Rescale image to uint8 0-255
    img[img < 0] = 0

    if np.max(img) == 0:
        img = np.uint8(255*img)
    else:
        img = np.uint8(255*img/np.max(img))

    features['image'] = img
    features['binary'] = 255*bw_img_all

    # Save the binary image and also color image if requested
    if save_to_disk:

        #try:

        # convert and save images

        # Raw color (no background removal)
        if use_jpeg:
            if raw_color:
                cv2.imwrite(os.path.join(abs_path,file_prefix+"_rawcolor.jpeg"),features['rawcolor'])
            # Save the processed image and binary mask
            cv2.imwrite(os.path.join(abs_path,file_prefix+".jpeg"),features['image'])
        else:
            if raw_color:
                cv2.imwrite(os.path.join(abs_path,file_prefix+"_rawcolor.png"),features['rawcolor'])
            # Save the processed image and binary mask
            cv2.imwrite(os.path.join(abs_path,file_prefix+".png"),features['image'])

        # Binary should also be saved png
        cv2.imwrite(os.path.join(abs_path,file_prefix+"_binary.png"),features['binary'])


    return features
