import cv2
import pytest
import sys,os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from lib.camera_helper import CameraHelper

class BlurDetection:
    def __init__(self):
        self.threshold = 100.0
        self.camera_helper = None

    def is_blurry(self, image, threshold=None):
        if threshold is not None:
            self.threshold = threshold
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        return variance < self.threshold

    def set_camera(self, camera_helper):
        self.camera_helper = camera_helper

    def test_image_blur(self):
        if not self.camera_helper or not self.camera_helper.camera:
            raise RuntimeError("Camera not initialized")
        grab_result = self.camera_helper.camera.GrabOne(1000)
        img = grab_result.Array
        return not self.is_blurry(img)

# Test fixtures and functions for pytest
@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_blur_detection(camera):
    detector = BlurDetection()
    detector.set_camera(camera)
    assert detector.test_image_blur(), "The image appears to be blurry."
