import cv2
import numpy as np
import pytest
from lib.genicam_helper import GenICamHelper
from lib.camera_helper import CameraHelper

@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def compute_brightness(img):
    return np.mean(img)

def compute_contrast(img):
    return np.std(img)

def test_image_quality(camera):
    grab_result = camera.camera.GrabOne(1000)
    img = grab_result.Array

    brightness = compute_brightness(img)
    contrast = compute_contrast(img)

    assert 50 <= brightness <= 200, f"Image brightness {brightness} is out of range!"
    assert contrast >= 50, f"Image contrast {contrast} is too low!"
