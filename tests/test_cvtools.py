import pickle
import unittest
from collections import OrderedDict

import cv2
import numpy as np

from cvtools import quick_features, import_image, convert_to_8bit


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
        self.fail("TODO - test calculated values")

    def test_raw_object_regression(self):
        raw_8bit = convert_to_8bit(self.raw_image)
        features = quick_features(raw_8bit)
        with open("expected/case_1_blob_qf.pickle", "rb") as f:
            expected_features = pickle.load(f)

        # pickle.dump(features, open("expected/case_1_blob_qf.pickle", "wb"))
        expect_rep = sorted(expected_features)
        features_rep = sorted(features)
        self.assertEqual(str(expect_rep), str(features_rep))
