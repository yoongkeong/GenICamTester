import pytest
from funct.funct_powercycle import PowerCycleTest


def test_power_cycle_minimal(camera_helper):
    pct = PowerCycleTest()
    pct.set_camera(camera_helper)
    # Reduce cycles for speed in CI / simulation
    pct.set_test_parameters(cycles=1, cycle_delay=0.2)
    results = pct.run_power_cycle_test()
    # With 1 cycle we expect either success or failure but code path exercised
    assert results['total_cycles'] == 1
    assert results['successful_cycles'] + results['failed_cycles'] == 1
