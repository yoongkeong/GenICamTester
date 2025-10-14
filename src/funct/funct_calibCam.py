import cv2
import numpy as np
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.camera_helper import CameraHelper

class CameraCalibration:
    def __init__(self):
        self.camera_helper = None
        self.checkerboard = (7, 7)  # default checkerboard size
        self.objpoints = []  # 3d points in real world space
        self.imgpoints = []  # 2d points in image plane
        self.camera_matrix = None
        self.dist_coeffs = None

    def set_camera(self, camera_helper):
        self.camera_helper = camera_helper

    def set_checkerboard_size(self, width, height):
        self.checkerboard = (width, height)

    def calibrate_camera(self, images):
        """Calibrate camera using provided checkerboard images"""
        objp = np.zeros((self.checkerboard[0] * self.checkerboard[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:self.checkerboard[0], 0:self.checkerboard[1]].T.reshape(-1, 2)

        for img in images:
            # Support grayscale frames directly
            if len(img.shape) == 2 or (len(img.shape) == 3 and img.shape[2] == 1):
                gray = img
            else:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            ret, corners = cv2.findChessboardCorners(gray, self.checkerboard, None)
            
            if ret:
                self.objpoints.append(objp)
                corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1),
                                          (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
                self.imgpoints.append(corners2)

        if len(self.objpoints) > 0:
            ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                self.objpoints, self.imgpoints, gray.shape[::-1], None, None)
            self.camera_matrix = mtx
            self.dist_coeffs = dist
            return True
        return False

    def capture_calibration_image(self):
        """Capture an image from the camera for calibration"""
        if not self.camera_helper or not self.camera_helper.camera:
            raise RuntimeError("Camera not initialized")
        grab_result = self.camera_helper.camera.GrabOne(1000)
        return grab_result.Array

    def undistort_image(self, img):
        """Undistort an image using the calibration results"""
        if self.camera_matrix is None or self.dist_coeffs is None:
            raise RuntimeError("Camera not calibrated yet")
        return cv2.undistort(img, self.camera_matrix, self.dist_coeffs)

# Embedded standalone tests removed; see tests in src/tests
