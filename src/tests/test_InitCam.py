# test_InitCam.py
import pytest
from src.lib.camera_helper import CameraHelper

def get_available_cameras():
    """Get a list of all available cameras."""
    return CameraHelper.get_available_cameras()

@pytest.fixture(scope='module')
def camera_config():
    # Modify here if you want to change between DHCP or manual configuration.
    return {
        'use_dhcp': False,  # Set True for DHCP, False for manual IP
        'ip_address': "192.168.1.10",
        'subnet_mask': "255.255.255.0",
        'gateway': "192.168.1.1"
    }

@pytest.fixture(scope='module')
def camera(camera_config):
    camera_helper = CameraHelper()

    # Connect to the camera with DHCP or manual IP configuration
    if camera_config['use_dhcp']:
        camera_helper.connect_camera(use_dhcp=True)
    else:
        camera_helper.connect_camera(
            ip_address=camera_config['ip_address'],
            subnet_mask=camera_config['subnet_mask'],
            gateway=camera_config['gateway']
        )
    
    yield camera_helper
    camera_helper.disconnect_camera()

def test_initialize_camera(camera):
    assert camera.camera.IsOpen(), "Camera failed to initialize."
