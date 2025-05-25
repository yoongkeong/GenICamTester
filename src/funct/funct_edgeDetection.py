import cv2
import pytest
from src.lib.camera_helper import CameraHelper

@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_edge_detection(camera):
    grab_result = camera.camera.GrabOne(1000)
    img = grab_result.Array

    edges = cv2.Canny(img, 100, 200)  # Perform edge detection
    assert edges is not None, "Edge detection failed."
    assert edges.sum() > 0, "No edges detected in the image."
