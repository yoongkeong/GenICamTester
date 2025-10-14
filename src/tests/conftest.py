import pytest
import os, sys
from lib.camera_helper import CameraHelper


def pytest_addoption(parser):
    parser.addoption("--simulate", action="store_true", default=False, help="Run tests using simulation camera")


@pytest.fixture(scope="session")
def simulate(request):
    return request.config.getoption("--simulate")


@pytest.fixture(scope="session")
def camera_helper(simulate):
    helper = CameraHelper(simulate=simulate)
    if simulate:
        helper.connect_camera(None)
    else:
        # Attempt to enumerate first available camera; skip tests if none
        cams = helper.enumerate_cameras()
        if not cams:
            pytest.skip("No physical cameras found and simulation not enabled")
        helper.connect_camera(cams[0])
    yield helper
    try:
        helper.disconnect_camera()
    except Exception:
        pass


@pytest.fixture(scope="session")
def genicam_helper(camera_helper):
    from lib.genicam_helper import GenICamHelper
    gh = GenICamHelper()
    gh.set_camera(camera_helper.camera)
    return gh
