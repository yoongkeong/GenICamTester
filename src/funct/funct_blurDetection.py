import cv2
import pytest
from camera_helper import CameraHelper

def is_blurry(image, threshold=100.0):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = laplacian.var()
    return variance < threshold

@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_blur_detection(camera):
    grab_result = camera.camera.GrabOne(1000)
    img = grab_result.Array

    blur = is_blurry(img)
    assert not blur, "The image appears to be blurry."
