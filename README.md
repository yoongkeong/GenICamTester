# GenICamTester
Generic industrial camera (GenICAM) tester based on Pypylon.

---

## Requirements
- Covered general testing of GenICAM cameras USB/GigE

## Build instruction

<div style="display: flex; justify-content: center; gap: 20px;">
  <div style="text-align: center;">
    <img src="Tech_stack.png" alt="Tech Stack" width="400">
    <p><b>Packages utilised</b></p>
  </div>
  <div style="text-align: center;">
    <img src="Block_diagram.jpg" alt="Block Diagram" width="400">
    <p><b>System diagram</b></p>
  </div>
</div>

---

## File Structure

### Configuration Files
- **config/**  
  - `config.ini` — General configurations for tests.  
  - `camera_settings.json` — Camera-specific settings (e.g., resolutions, modes).  

### Test Resources
- **data/**  
  - `test_images/` — Images used for image quality tests.  
  - `calibration_files/` — Calibration files for camera testing.  

### Documentation
- **docs/**  
  - `architecture.md` — High-level architecture description of the tester.  
  - `test_plan.md` — Detailed test plans for the modules.  
  - `test_report_template.md` — Template for test reports.  

### Logs
- **logs/**  
  - `test.log` — Main log file for test runs.  
  - `error.log` — Log for errors and exceptions.  

### Reports
- **reports/**  
  - `coverage/` — Test coverage reports (HTML).  

### Source Code
- **src/**  
  - **GUI**  
    - `main_gui.py` — Main GUI script.  
  - **Libraries**  
    - `camera_helper.py` — Functions for camera control (start/stop, init).  
    - `genicam_helper.py` — Utilities for working with GenICam API (XML parsing, feature access).  
    - `image_helper.py` — Functions for image processing (OpenCV functions).  
    - `utils.py` — General utility functions (logging, error handling).  
  - **Tests**  
    - `test_power.py` — Power ON and cycle tests.  
    - `test_image_acquisition.py` — Image acquisition, FPS tests.  
    - `test_feature_access.py` — Test for GenICam feature access (dynamic discovery).  
    - `test_trigger_strobe.py` — Trigger, strobe, sync tests.  
    - `test_multicam.py` — Multi-camera synchronization tests.  
    - `test_roi.py` — User-defined ROI and event handling tests.  
    - `test_image_quality.py` — Sharpness, color accuracy, noise, edge detection.  
  - `__main__.py` — Entry point script (CLI for running tests, optional).  

### Additional Files
- `.env` — Environment variables (optional, for sensitive info).  
- `.gitignore` — Gitignore file for ignoring unnecessary files.  
- `pytest.ini` — Pytest configuration (reporting, test paths).  
- `requirements.txt` — List of dependencies (pypylon, pytest, pytest-cov, etc.).  
- `README.md` — Overview and setup guide for the project.  

---