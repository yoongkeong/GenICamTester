"""Dump GenICam node map for the first detected camera and save to node_dump.txt

This script connects to the first available camera using CameraHelper, attaches it to
GenICamHelper, enumerates available nodes, and writes a human-readable dump to
node_dump.txt in project root.
"""
import os
import sys
import logging
# Ensure src/ is on sys.path so local package imports (lib.*) work when running this script
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.camera_helper import CameraHelper
from lib.genicam_helper import GenICamHelper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTFILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'node_dump.txt'))


def dump():
    ch = CameraHelper()
    cameras = CameraHelper.enumerate_cameras()
    if not cameras:
        logger.error("No cameras found to dump nodes")
        return 1

    cam_info = cameras[0]
    logger.info(f"Using camera: {cam_info}")

    try:
        ch.connect_camera(cam_info)
        cam = ch.camera
        gh = GenICamHelper()
        gh.set_camera(cam)

        lines = []
        lines.append(f"Camera info: {cam_info}\n")

        # Try using node map
        try:
            node_map = cam.GetNodeMap()
            try:
                nodes = list(node_map.GetNodes())
            except Exception:
                # Older pypylon might not support GetNodes(); try iterating by name list
                nodes = []
                try:
                    # Some node maps expose _nodes or similar
                    nodes = list(node_map)
                except Exception:
                    nodes = []

            if nodes:
                lines.append(f"Found {len(nodes)} nodes via NodeMap.GetNodes()\n")
                for n in nodes:
                    try:
                        name = getattr(n, 'GetName', lambda: str(n))()
                    except Exception:
                        name = str(n)
                    val = None
                    for getter in ('GetValue', 'GetFloatValue', 'GetIntValue', 'GetSymbolic'):
                        try:
                            val = getattr(n, getter)()
                            break
                        except Exception:
                            continue
                    lines.append(f"{name}: {val}")
            else:
                lines.append("NodeMap.GetNodes() returned no entries; falling back to attribute scan\n")
        except Exception as e:
            lines.append(f"Failed to use NodeMap: {e}\n")

        # Fallback: scan common attribute names or camera attributes
        try:
            attrs = dir(cam)
            scanned = 0
            for a in attrs:
                if a.startswith('_'):
                    continue
                try:
                    obj = getattr(cam, a)
                except Exception:
                    continue
                # Try to detect node-like objects by presence of GetValue or GetSymbolic
                if any(hasattr(obj, m) for m in ('GetValue', 'GetFloatValue', 'GetIntValue', 'GetSymbolic')):
                    try:
                        val = None
                        for getter in ('GetValue', 'GetFloatValue', 'GetIntValue', 'GetSymbolic'):
                            if hasattr(obj, getter):
                                try:
                                    val = getattr(obj, getter)()
                                    break
                                except Exception:
                                    continue
                        lines.append(f"{a}: {val}")
                        scanned += 1
                    except Exception:
                        continue
            lines.append(f"\nScanned {scanned} attribute-like nodes from camera object")
        except Exception as e:
            lines.append(f"Attribute scan failed: {e}")

        # Write to file
        with open(OUTFILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        logger.info(f"Node dump written to {OUTFILE}")
        return 0

    except Exception as e:
        logger.exception(f"Failed to dump nodes: {e}")
        return 2
    finally:
        try:
            ch.disconnect_camera()
        except Exception:
            pass


if __name__ == '__main__':
    import sys
    sys.exit(dump())
