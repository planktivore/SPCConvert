import pickle
import unittest
from collections import OrderedDict

import cv2
import numpy as np
import scipy.spatial.distance as distance

from cvtools import quick_features, import_image, convert_to_8bit, intensity_features


class TestFeatures(unittest.TestCase):
    def setUp(self):
        np.random.seed(1)
        self.raw_image = import_image("input", "case_1_blob.tif", bayer_pattern=cv2.COLOR_BAYER_BG2RGB)
        self.red_blob = np.zeros((30, 20, 3), dtype=np.uint8)
        self.red_blob += np.random.random_integers(0, 2, (30, 20, 3)).astype(np.uint8)
        # square 3 x 5 no corners
        self.red_blob[5:8, 2:7, 0] = 129
        self.red_blob[5, 2, 0] = 0
        self.red_blob[5, 6, 0] = 0
        self.red_blob[7, 2, 0] = 0
        self.red_blob[7, 6, 0] = 0

    def test_simple_object(self):
        features = quick_features(self.red_blob)

        blob_mask = np.uint8(np.mean(self.red_blob, 2)) > 0
        diff = blob_mask != (features['binary'] > 0)
        self.assertLess(np.count_nonzero(diff), 4)
        # uses edges so it is slightly different
        self.assertEqual(14, features['area'])
        self.assertAlmostEqual(6.876, features['major_axis_length'], 2)
        self.assertAlmostEqual(2.781, features['minor_axis_length'], 2)
        self.assertAlmostEqual(0.068, features['orientation'], 2)
        self.assertEqual(0.01, features['clipped_fraction'])

    def test_intensity_object(self):
        red_blue_blob = self.red_blob.copy()
        red_blue_blob[5:8, 2:7, 1] = 20
        features = quick_features(red_blue_blob)
        # test only that they are calculated for all colours
        # and added to results

        self.fail("TODO - test calculated values")

    def test_intensity_measures_rect(self):
        # std, quartile intensity
        square = np.zeros((20, 20), dtype=np.uint8)
        square[5:10, 10:16] = 5  # 5 x 6 square (30 pixels)
        square[10:11, 10:16] = 20  # one stripe is stronger (6 pixels)
        features = intensity_features(square, square > 0)
        self.assertEqual((5 * 30 + 20 * 6) / 36.0, features['mean_intensity'])
        self.assertEqual(5, features['median_intensity'])
        self.assertAlmostEqual(5.59017, features['std_intensity'], 3)
        self.assertAlmostEqual(5, features['perc_25_intensity'], 3)
        self.assertAlmostEqual(5, features['perc_75_intensity'], 3)

        centroid = np.array([7.5, 12.5])
        weighted_x = 12.5
        weighted_y = (7 * 150 + 10 * 120) / 270.0
        weighted = np.array([weighted_y, weighted_x])

        expected_displacement = distance.euclidean(weighted, centroid)
        expected_displacement_image = expected_displacement / 20.0
        expected_displacement_relative = expected_displacement / 6.8313
        self.assertAlmostEqual(expected_displacement_image, features['mass_displace_in_images'], 3)
        self.assertAlmostEqual(expected_displacement_relative, features['mass_displace_in_minors'], 3)

    def test_intensity_measures_circle(self):
        # test with circle
        # circle will have some gradient
        self.fail("TODO")

    def test_raw_object_regression(self):
        raw_8bit = convert_to_8bit(self.raw_image)
        features = quick_features(raw_8bit)
        with open("expected/case_1_blob_qf.pickle", "rb") as f:
            expected_features = pickle.load(f)

        # pickle.dump(features, open("expected/case_1_blob_qf.pickle", "wb"))
        expect_rep = sorted(expected_features)

        # ignore added features
        del features['solidity']
        del features['estimated_volume']
        del features['eccentricity']
        for k in [k for k in features.keys() if 'intensity' in k]:
            del features[k]

        features_rep = sorted(features)
        self.assertEqual(str(expect_rep), str(features_rep))
