# main.py

import sys
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
from tests.test_InitCam import TestInitializeCamera
from tests.test_IO import TestIO
from tests.test_maxFPS import TestMaxFPS
from tests.test_multicam import TestMultiCam
from tests.test_powerGigE import TestPowerGigE
from tests.test_powerUSB import TestPowerUSB
from tests.test_ROI import TestROI

def main():
    # Initialize the QApplication for the GUI
    app = QApplication(sys.argv)
    
    # Initialize CameraTestGUI
    gui = CameraTestGUI()
    
    # Initialize and set up helpers
    camera_helper = CameraHelper()
    driver_helper = DriverHelper()
    genicam_helper = GenICamHelper()
    
    # Set up helpers in the presenter
    gui.presenter.set_camera_helper(camera_helper)
    gui.presenter.set_driver_helper(driver_helper)
    gui.presenter.set_genicam_helper(genicam_helper)
    
    # Initialize functional modules
    blur_detection = BlurDetection()
    camera_calibration = CameraCalibration()
    edge_detection = EdgeDetection()
    long_run_test = LongRunTest()
    power_cycle_test = PowerCycleTest()

    # Initialize test modules
    test_feature_access = TestFeatureAccess()
    test_image_acq = TestImageAcquisition()
    test_img_quality = TestImageQuality()
    test_init_cam = TestInitializeCamera()
    test_io = TestIO()
    test_max_fps = TestMaxFPS()
    test_multicam = TestMultiCam()
    test_power_gige = TestPowerGigE()
    test_power_usb = TestPowerUSB()
    test_roi = TestROI()

    # Link GUI actions with functionality
    gui.presenter.set_camera_helper(camera_helper)
    gui.presenter.set_driver_helper(driver_helper)
    gui.presenter.set_genicam_helper(genicam_helper)

    gui.presenter.add_functionality("blur_detection", blur_detection)
    gui.presenter.add_functionality("camera_calibration", camera_calibration)
    gui.presenter.add_functionality("edge_detection", edge_detection)
    gui.presenter.add_functionality("long_run_test", long_run_test)
    gui.presenter.add_functionality("power_cycle_test", power_cycle_test)

    gui.presenter.add_test("test_feature_access", test_feature_access)
    gui.presenter.add_test("test_image_acq", test_image_acq)
    gui.presenter.add_test("test_img_quality", test_img_quality)
    gui.presenter.add_test("test_init_cam", test_init_cam)
    gui.presenter.add_test("test_io", test_io)
    gui.presenter.add_test("test_max_fps", test_max_fps)
    gui.presenter.add_test("test_multicam", test_multicam)
    gui.presenter.add_test("test_power_gige", test_power_gige)
    gui.presenter.add_test("test_power_usb", test_power_usb)
    gui.presenter.add_test("test_roi", test_roi)

    # Show the GUI
    gui.show()
    
    # Start the main event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
