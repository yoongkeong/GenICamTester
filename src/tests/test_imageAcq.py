# test_imageAcq.py
import pytest
from src.lib.genicam_helper import GenICamHelper
from src.lib.camera_helper import CameraHelper
from PyQt5.QtGui import QImage, QPixmap

@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_image_acquisition(camera, gui):
    grab_result = camera.camera.GrabOne(1000)
    assert grab_result.GrabSucceeded(), f"Image acquisition failed with error: {grab_result.GetErrorDescription()}"

    # Convert the image to QImage and show on GUI
    image = grab_result.GetArray()
    height, width = image.shape
    qimage = QImage(image.data, width, height, QImage.Format_Grayscale8)
    pixmap = QPixmap.fromImage(qimage)
    gui.display_image(pixmap)
