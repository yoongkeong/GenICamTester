import cv2
import numpy as np
import pytest
from src.lib.camera_helper import CameraHelper

def calibrate_camera(images, checkerboard=(7,7)):
    objpoints = []  # 3d points in real world space
    imgpoints = []  # 2d points in image plane

    objp = np.zeros((checkerboard[0]*checkerboard[1],3), np.float32)
    objp[:,:2] = np.mgrid[0:checkerboard[0],0:checkerboard[1]].T.reshape(-1,2)

    for img in images:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, checkerboard, None)
        if ret:
            imgpoints.append(corners)
            objpoints.append(objp)

    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)
    return ret, mtx, dist, rvecs, tvecs

@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_camera_calibration(camera):
    images = []
    for _ in range(10):
        grab_result = camera.camera.GrabOne(1000)
        images.append(grab_result.Array)

    ret, mtx, dist, rvecs, tvecs = calibrate_camera(images)
    assert ret, "Camera calibration failed."
    assert len(mtx) > 0, "Calibration matrix is empty."
