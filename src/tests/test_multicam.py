import time
import threading
import pytest
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.genicam_helper import GenICamHelper
from lib.camera_helper import CameraHelper

class TestMultiCam:
    def __init__(self):
        self.cameras = []
        self.genicam_helpers = []
        self.test_duration = 10  # seconds
        self.sync_threshold = 1000  # microseconds

    def setup(self, camera_list):
        """Set up multiple cameras for testing"""
        for camera in camera_list:
            genicam = GenICamHelper()
            genicam.set_camera(camera.camera)
            self.cameras.append(camera)
            self.genicam_helpers.append(genicam)

    def set_test_parameters(self, duration=10, sync_threshold=1000):
        """Set test parameters"""
        self.test_duration = duration
        self.sync_threshold = sync_threshold

    def test_synchronization(self):
        """Test synchronization between multiple cameras"""
        if not self.cameras or len(self.cameras) < 2:
            raise RuntimeError("Need at least 2 cameras for synchronization test")

        results = {
            "sync_accuracy": [],
            "frame_counts": [],
            "fps_values": [],
            "overall_success": False
        }

        try:
            # Start all cameras
            threads = []
            frame_queues = []
            
            for camera in self.cameras:
                queue = []
                frame_queues.append(queue)
                thread = threading.Thread(
                    target=self._grab_frames,
                    args=(camera, queue)
                )
                threads.append(thread)
                thread.start()

            # Wait for threads to finish
            for thread in threads:
                thread.join()

            # Analyze results
            results["frame_counts"] = [len(q) for q in frame_queues]
            
            # Calculate FPS for each camera
            for queue in frame_queues:
                if len(queue) > 1:
                    duration = (queue[-1] - queue[0]) / 1e9  # Convert ns to seconds
                    fps = (len(queue) - 1) / duration
                    results["fps_values"].append(fps)
                else:
                    results["fps_values"].append(0)

            # Check synchronization between cameras
            sync_errors = []
            for i in range(min(results["frame_counts"])):
                timestamps = [q[i] for q in frame_queues]
                max_diff = max(timestamps) - min(timestamps)
                sync_errors.append(max_diff / 1000)  # Convert to microseconds

            results["sync_accuracy"] = {
                "max_error": max(sync_errors) if sync_errors else float('inf'),
                "avg_error": sum(sync_errors) / len(sync_errors) if sync_errors else float('inf')
            }

            # Determine overall success
            results["overall_success"] = (
                all(fps > 0 for fps in results["fps_values"]) and
                results["sync_accuracy"]["max_error"] <= self.sync_threshold
            )

        except Exception as e:
            results["error"] = str(e)

        return results

    def _grab_frames(self, camera, queue):
        """Grab frames from a camera and store their timestamps"""
        try:
            start_time = time.time()
            camera.camera.StartGrabbing()
            
            while time.time() - start_time < self.test_duration:
                grab_result = camera.camera.RetrieveResult(1000)
                if grab_result.GrabSucceeded():
                    queue.append(grab_result.TimeStamp)
                grab_result.Release()
                
        finally:
            if camera.camera.IsGrabbing():
                camera.camera.StopGrabbing()

    def cleanup(self):
        """Clean up resources"""
        for camera in self.cameras:
            try:
                if camera.camera.IsGrabbing():
                    camera.camera.StopGrabbing()
            except:
                pass

# Test fixtures and functions for pytest
@pytest.fixture(scope='module')
def cameras():
    # Initialize two test cameras
    camera1 = CameraHelper()
    camera2 = CameraHelper()
    
    camera1.connect_camera(ip_address="192.168.1.10")
    camera2.connect_camera(ip_address="192.168.1.11")
    
    yield [camera1, camera2]
    
    camera1.disconnect_camera()
    camera2.disconnect_camera()

def test_multicam_sync(cameras):
    test = TestMultiCam()
    test.setup(cameras)
    test.set_test_parameters(duration=5)  # Shorter test for pytest
    
    results = test.test_synchronization()
    assert results["overall_success"], "Multi-camera synchronization test failed"
    assert results["sync_accuracy"]["max_error"] <= 1000, "Sync error too high"
    assert all(fps > 0 for fps in results["fps_values"]), "Some cameras not capturing frames"
