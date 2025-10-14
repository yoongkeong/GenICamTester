import pytest
from funct.funct_longRun import LongRunTest


def test_long_run_short(camera_helper):
    tst = LongRunTest()
    tst.set_camera(camera_helper)
    tst.set_duration(2)  # 2 seconds quick smoke
    results = tst.start_test()
    assert results['frames_captured'] >= 1
    assert results['errors'] == 0
