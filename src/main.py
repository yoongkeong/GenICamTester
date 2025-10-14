# main.py

import sys
import argparse
import os
import logging
import time
import threading
import socket
import struct
import numpy as np
import cv2
from PIL import Image
import matplotlib.pyplot as plt
from typing_extensions import TypedDict
import requests
from loguru import logger

from PyQt5.QtWidgets import QApplication
from gui.main_gui import CameraTestGUI
from funct.funct_blurDetection import BlurDetection
from funct.funct_calibCam import CameraCalibration
from funct.funct_edgeDetection import EdgeDetection
from funct.funct_longRun import LongRunTest
from funct.funct_powercycle import PowerCycleTest
from lib.camera_helper import CameraHelper
from lib.driver_helper import DriverHelper
from lib.genicam_helper import GenICamHelper
from tests.test_featureAccess import TestFeatureAccess
from tests.test_imageAcq import TestImageAcquisition
from tests.test_imgQuality import TestImageQuality
from tests.test_maxFPS import TestMaxFPS
from tests.test_multicam import TestMultiCam
from tests.test_powerGigE import TestPowerGigE
from tests.test_powerUSB import TestPowerUSB

def main():
    try:
        parser = argparse.ArgumentParser(description="GenICam Tester")
        parser.add_argument('--simulate', action='store_true', help='Force simulation camera mode')
        args, qt_args = parser.parse_known_args()

        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        logger.info("Starting GenICam Tester application...")

        # Initialize the QApplication for the GUI
        app = QApplication(qt_args)
        logger.info("QApplication initialized successfully")

        # Initialize CameraTestGUI
        gui = CameraTestGUI()
        logger.info("CameraTestGUI initialized successfully")

        # Initialize and set up helpers
        camera_helper = CameraHelper(simulate=args.simulate)
        driver_helper = DriverHelper()
        genicam_helper = GenICamHelper()
        logger.info("Helper modules initialized successfully")

        # Set up helpers in the presenter
        gui.presenter.set_camera_helper(camera_helper)
        gui.presenter.set_driver_helper(driver_helper)
        gui.presenter.set_genicam_helper(genicam_helper)
        logger.info("Helpers set in presenter successfully")

        # Initialize functional modules
        blur_detection = BlurDetection()
        camera_calibration = CameraCalibration()
        edge_detection = EdgeDetection()
        long_run_test = LongRunTest()
        power_cycle_test = PowerCycleTest()
        logger.info("Functional modules initialized successfully")

        # Initialize test modules
        test_feature_access = TestFeatureAccess()
        test_image_acq = TestImageAcquisition()
        test_img_quality = TestImageQuality()
    # Note: Initialization & IO tests converted to internal functional implementations
    # in presenter (no longer class-based), so we skip creating test objects here.
        test_max_fps = TestMaxFPS()
        test_multicam = TestMultiCam()
        test_power_gige = TestPowerGigE()
        test_power_usb = TestPowerUSB()
        logger.info("Test modules initialized successfully")

        # Link GUI actions with functionality
        gui.presenter.add_functionality("blur_detection", blur_detection)
        gui.presenter.add_functionality("camera_calibration", camera_calibration)
        gui.presenter.add_functionality("edge_detection", edge_detection)
        gui.presenter.add_functionality("long_run_test", long_run_test)
        gui.presenter.add_functionality("power_cycle_test", power_cycle_test)
        logger.info("Functionality linked to presenter successfully")

        gui.presenter.add_test("test_feature_access", test_feature_access)
        gui.presenter.add_test("test_image_acq", test_image_acq)
        gui.presenter.add_test("test_img_quality", test_img_quality)
    # test_init_cam & test_io no longer registered as external test objects
        gui.presenter.add_test("test_max_fps", test_max_fps)
        gui.presenter.add_test("test_multicam", test_multicam)
        gui.presenter.add_test("test_power_gige", test_power_gige)
        gui.presenter.add_test("test_power_usb", test_power_usb)
    # ROI test now functional-only in pytest; not instantiated here.
        logger.info("Test modules linked to presenter successfully")

        # Show the GUI
        gui.show()
        if camera_helper.simulation_enabled:
            logger.info("Simulation mode enabled (requested via CLI)")
        logger.info("GUI displayed successfully")

        # Start the main event loop
        logger.info("Starting main event loop...")
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"Error during application startup: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
