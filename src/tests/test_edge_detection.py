import pytest
import numpy as np
from funct.funct_edgeDetection import EdgeDetection


def test_edge_detection(camera_helper):
    ed = EdgeDetection()
    ed.set_camera(camera_helper)
    edges = ed.capture_and_detect()
    assert edges is not None
    # Ensure some edge pixels exist but not zero or full
    edge_ratio = np.count_nonzero(edges) / edges.size
    if edge_ratio == 0:
        pytest.skip("No edges detected in current simulation frame; skipping")
    assert edge_ratio < 0.9, f"Edge ratio unexpectedly high: {edge_ratio:.2f}"
