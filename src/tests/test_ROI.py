import pytest
from lib.genicam_helper import GenICamHelper


@pytest.fixture(scope="module")
def roi_helpers(camera_helper):
    gh = GenICamHelper()
    gh.set_camera(camera_helper.camera)
    return gh


def _capture(camera):
    grab = camera.GrabOne(500)
    if not grab or not grab.GrabSucceeded():
        raise RuntimeError("Failed to grab frame")
    arr = grab.Array
    grab.Release()
    return arr


def test_roi_variants(camera_helper, roi_helpers):
    gh = roi_helpers
    # Get current (used as max in simulation)
    try:
        max_w, max_h = gh.get_max_resolution()
    except Exception:
        pytest.skip("Max resolution not available")

    # Full
    gh.set_roi(max_w, max_h)
    img = _capture(camera_helper.camera)
    assert img.shape[1] == max_w and img.shape[0] == max_h, "Full resolution mismatch"

    # Half
    half_w, half_h = max_w // 2, max_h // 2
    gh.set_roi(half_w, half_h)
    img = _capture(camera_helper.camera)
    assert img.shape[1] == half_w and img.shape[0] == half_h, "Half resolution mismatch"

    # Quarter
    q_w, q_h = max_w // 4, max_h // 4
    gh.set_roi(q_w, q_h)
    img = _capture(camera_helper.camera)
    assert img.shape[1] == q_w and img.shape[0] == q_h, "Quarter resolution mismatch"

    # Custom (third) - without offsets since helper lacks offset API
    c_w, c_h = max_w // 3, max_h // 3
    gh.set_roi(c_w, c_h)
    img = _capture(camera_helper.camera)
    assert img.shape[1] == c_w and img.shape[0] == c_h, "Custom ROI mismatch"
