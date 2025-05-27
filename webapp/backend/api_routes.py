from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
import os
from datetime import datetime

# Add parent directory to path to import GenICamTester modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import test modules
from src.tests import (
    test_InitCam, test_imageAcq, test_featureAccess, test_ROI,
    test_powerUSB, test_powerGigE, test_multicam, test_maxFPS,
    test_IO, test_imgQuality
)

router = APIRouter(prefix="/api")

class TestConfig(BaseModel):
    camera_id: str
    tests: List[str]
    parameters: Optional[Dict] = None

class TestReport(BaseModel):
    test_id: str
    camera_id: str
    test_name: str
    status: str
    result: Dict
    timestamp: datetime
    error: Optional[str] = None

# Store test results in memory (replace with database in production)
test_history: List[TestReport] = []

@router.get("/cameras")
async def get_cameras():
    """Get list of available cameras"""
    try:
        from src.lib.camera_helper import CameraHelper
        cameras = CameraHelper.enumerate_cameras()
        return {
            "status": "success",
            "cameras": cameras
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/run")
async def run_tests(config: TestConfig, background_tasks: BackgroundTasks):
    """Run selected tests for a camera"""
    try:
        print(f"Running tests for camera {config.camera_id}: {config.tests}")
        results = []
        
        # Map of test IDs to test classes
        available_tests = {
            "initialization": test_InitCam.test_InitCam,
            "image_acquisition": test_imageAcq.test_imageAcq,
            "feature_access": test_featureAccess.test_featureAccess,
            "roi": test_ROI.test_ROI,
            "power_usb": test_powerUSB.test_powerUSB,
            "power_gige": test_powerGigE.test_powerGigE,
            "multicam": test_multicam.test_multicam,
            "max_fps": test_maxFPS.test_maxFPS,
            "io_test": test_IO.test_IO,
            "image_quality": test_imgQuality.test_imgQuality
        }

        # Run each selected test
        for test_name in config.tests:
            if test_name in available_tests:
                print(f"Running test: {test_name}")
                test_class = available_tests[test_name]()
                result = test_class.run(config.camera_id, config.parameters)
                
                test_report = TestReport(
                    test_id=f"{test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    camera_id=config.camera_id,
                    test_name=test_name,
                    status="success" if result.get("success", False) else "error",
                    result=result,
                    timestamp=datetime.now(),
                    error=result.get("error")
                )
                
                test_history.append(test_report)
                results.append(test_report.dict())
                print(f"Test {test_name} completed with status: {test_report.status}")

        return {
            "status": "success",
            "message": "Tests executed successfully",
            "results": results
        }
    except Exception as e:
        print(f"Error running tests: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error running tests: {str(e)}"
        )

@router.get("/test/history/{camera_id}")
async def get_test_history(camera_id: str):
    """Get test history for a specific camera"""
    try:
        camera_tests = [test for test in test_history if test.camera_id == camera_id]
        return {
            "status": "success",
            "history": [test.dict() for test in camera_tests]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving test history: {str(e)}"
        )