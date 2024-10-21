import pypylon.pylon as pylon
import logging
from configparser import ConfigParser

config = ConfigParser()
config.read('config/config.ini')
logger = logging.getLogger(__name__)

class CameraHelper:
    def __init__(self, camera_ip=None):
        self.camera_ip = camera_ip or config['gigE']['camera_ip']
        self.camera = self.initialize_camera()

    def initialize_camera(self):
        try:
            logger.info(f"Initializing camera at {self.camera_ip}")
            camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            camera.Open()
            return camera
        except Exception as e:
            logger.error(f"Camera initialization failed: {str(e)}")
            raise e

    def start_acquisition(self):
        try:
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            logger.info("Camera acquisition started")
        except Exception as e:
            logger.error(f"Failed to start acquisition: {str(e)}")
            raise e

    def stop_acquisition(self):
        self.camera.StopGrabbing()
        logger.info("Camera acquisition stopped")

    def power_on(self):
        logger.info("Powering on the camera")

    def power_off(self):
        logger.info("Powering off the camera")