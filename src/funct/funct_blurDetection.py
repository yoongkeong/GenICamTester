import cv2
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from lib.camera_helper import CameraHelper

class BlurDetection:
    def __init__(self):
        # Lower threshold suitable for high-contrast synthetic patterns
        self.threshold = 10.0
        self.camera_helper = None

    def is_blurry(self, image, threshold=None):
        if threshold is not None:
            self.threshold = threshold
        # Support grayscale frames produced by SimulationCamera
        if len(image.shape) == 2 or (len(image.shape) == 3 and image.shape[2] == 1):
            gray = image
        else:
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

# Embedded pytest fixtures/tests removed; see dedicated tests in src/tests
