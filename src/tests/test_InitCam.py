# test_InitCam.py
import pytest
import time


def test_camera_initialization(camera_helper):
    start = time.time()
    # camera_helper fixture already connected (physical or simulation)
    assert camera_helper.camera is not None and camera_helper.camera.IsOpen(), "Camera not open"
    # Try a quick frame grab to validate
    grab = camera_helper.camera.GrabOne(500)
    ok = grab and grab.GrabSucceeded()
    if grab:
        grab.Release()
    elapsed = time.time() - start
    assert ok, "Failed to grab test frame during initialization"
    assert elapsed >= 0, "Invalid timing"


def test_camera_verification(camera_helper):
    grab = camera_helper.camera.GrabOne(500)
    ok = grab and grab.GrabSucceeded()
    if grab:
        grab.Release()
    assert ok, "Camera verification failed"
