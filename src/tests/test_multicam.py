import pytest
import time
import logging
from src.lib.genicam_helper import GenICamHelper
from src.lib.camera_helper import CameraHelper
from pypylon import pylon

@pytest.fixture(scope='module')
def multicam_setup():
    factory = pylon.TlFactory.GetInstance()
    devices = factory.EnumerateDevices()

    if len(devices) < 2:
        raise RuntimeError("Less than two cameras found.")

    cameras = []
    for device in devices[:2]:  # Testing with 2 cameras for simplicity
        camera = pylon.InstantCamera(factory.CreateDevice(device))
        camera.Open()
        cameras.append(camera)
    
    yield cameras

    for camera in cameras:
        camera.Close()

def test_multicam_acquisition(multicam_setup):
    for camera in multicam_setup:
        grab_result = camera.GrabOne(1000)
        assert grab_result.GrabSucceeded(), "Image acquisition failed for one of the cameras."
        logging.info(f"Image acquired from camera: {camera.GetDeviceInfo().GetModelName()}")
