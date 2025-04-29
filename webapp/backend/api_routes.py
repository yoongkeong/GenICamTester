from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
import os
from datetime import datetime

# Add parent directory to path to import GenICamTester modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

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
        cameras = test_InitCam.get_available_cameras()
        return {"status": "success", "cameras": cameras}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/camera/{camera_id}")
async def get_camera_info(camera_id: str):
    """Get detailed information about a specific camera"""
    try:
        camera_info = test_InitCam.get_camera_info(camera_id)
        return {"status": "success", "camera": camera_info}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/test/run")
async def run_tests(config: TestConfig, background_tasks: BackgroundTasks):
    """Run specified tests on a camera"""
    test_mapping = {
        'initialization': test_InitCam.test_camera_init,
        'image_acquisition': test_imageAcq.test_image_acquisition,
        'feature_access': test_featureAccess.test_feature_access,
        'roi': test_ROI.test_roi,
        'power_usb': test_powerUSB.test_power,
        'power_gige': test_powerGigE.test_power,
        'multicam': test_multicam.test_multicam,
        'max_fps': test_maxFPS.test_max_fps,
        'io_test': test_IO.test_io,
        'image_quality': test_imgQuality.test_image_quality
    }

    results = []
    for test_name in config.tests:
        if test_name not in test_mapping:
            raise HTTPException(status_code=400, detail=f"Unknown test: {test_name}")
        
        try:
            test_func = test_mapping[test_name]
            # Run test with optional parameters
            if config.parameters and test_name in config.parameters:
                result = test_func(config.camera_id, **config.parameters[test_name])
            else:
                result = test_func(config.camera_id)

            report = TestReport(
                test_id=f"{config.camera_id}_{test_name}_{datetime.now().timestamp()}",
                camera_id=config.camera_id,
                test_name=test_name,
                status="success",
                result=result,
                timestamp=datetime.now()
            )
        except Exception as e:
            report = TestReport(
                test_id=f"{config.camera_id}_{test_name}_{datetime.now().timestamp()}",
                camera_id=config.camera_id,
                test_name=test_name,
                status="error",
                result={},
                timestamp=datetime.now(),
                error=str(e)
            )
        
        test_history.append(report)
        results.append(report)

    return {"status": "success", "results": results}

@router.get("/test/history/{camera_id}")
async def get_test_history(camera_id: str):
    """Get test history for a specific camera"""
    camera_history = [test for test in test_history if test.camera_id == camera_id]
    return {"status": "success", "history": camera_history}

@router.get("/test/latest/{camera_id}")
async def get_latest_results(camera_id: str):
    """Get most recent test results for a camera"""
    camera_history = [test for test in test_history if test.camera_id == camera_id]
    if not camera_history:
        return {"status": "success", "results": []}
    
    # Get most recent result for each test type
    latest_results = {}
    for test in reversed(camera_history):
        if test.test_name not in latest_results:
            latest_results[test.test_name] = test
    
    return {"status": "success", "results": list(latest_results.values())}