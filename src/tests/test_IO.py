import pytest
from lib.genicam_helper import GenICamHelper


def _io_line_test(genicam_helper, line_number):
    try:
        genicam_helper.set_line_mode(line_number, "input")
        input_state = genicam_helper.get_line_state(line_number)

        genicam_helper.set_line_mode(line_number, "output")
        genicam_helper.set_line_state(line_number, True)
        high_state = genicam_helper.get_line_state(line_number)

        genicam_helper.set_line_state(line_number, False)
        low_state = genicam_helper.get_line_state(line_number)

        return {
            "input_test": input_state is not None,
            "output_high": high_state is True,
            "output_low": low_state is False,
            "overall": True
        }
    except Exception as e:
        return {
            "input_test": False,
            "output_high": False,
            "output_low": False,
            "overall": False,
            "error": str(e)
        }


def _user_output_test(genicam_helper):
    try:
        genicam_helper.set_user_output(1, True)
        high_state = genicam_helper.get_user_output(1)
        genicam_helper.set_user_output(1, False)
        low_state = genicam_helper.get_user_output(1)
        return {"set_high": high_state is True, "set_low": low_state is False, "overall": True}
    except Exception as e:
        return {"set_high": False, "set_low": False, "overall": False, "error": str(e)}


def test_io_functionality(camera_helper, simulate):
    gh = GenICamHelper()
    gh.set_camera(camera_helper.camera)
    line1 = _io_line_test(gh, 1)
    line2 = _io_line_test(gh, 2)
    user_out = _user_output_test(gh)

    assert line1["overall"], f"IO Line 1 test failed: {line1}"
    assert line2["overall"], f"IO Line 2 test failed: {line2}"
    assert user_out["overall"], f"User output test failed: {user_out}"
