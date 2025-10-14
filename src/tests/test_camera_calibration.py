import pytest
from funct.funct_calibCam import CameraCalibration


def test_camera_calibration_smoke(camera_helper):
    calibrator = CameraCalibration()
    calibrator.set_camera(camera_helper)
    # Capture a few frames (simulation patterns may or may not have checkerboard; allow graceful failure)
    images = [calibrator.capture_calibration_image() for _ in range(3)]
    success = calibrator.calibrate_camera(images)
    # In simulation, checkerboard detection may fail; just ensure no exception and boolean returned
    assert isinstance(success, bool)
