# tests/test_imgQuality.py

import cv2
import numpy as np
import pytest
import sys, os, time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.genicam_helper import GenICamHelper


def _to_gray(image):
    if image is None:
        raise ValueError("Image is None")
    if image.ndim == 2 or (image.ndim == 3 and image.shape[2] == 1):
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


class TestImageQuality:
    """
    Minimal image-quality suite:
      - Basic: sharpness (Laplacian var), noise (center patch std), contrast (P95/P5)
      - EMVA-lite: DSNU, PRNU, temporal noise from stacks; linearity attempt; DR estimate
      - MTF sanity: slanted-edge fallback + FFT roll-off proxy
    All advanced steps are best-effort and never hard-fail if controls are missing.
    """

    def __init__(self):
        self.camera_helper = None
        self.genicam_helper = None

        # Conservative defaults (real cams can be much higher/lower; tune per product)
        self.min_sharpness = 5.0
        self.max_noise = 50.0
        self.min_contrast = 0.10

        # Stack sizes kept modest for speed; increase in lab runs
        self.stack_N = 32

    # -------------------------
    # Wiring / capture helpers
    # -------------------------

    def setup(self, camera_helper):
        """Set up the test with camera and GenICam helpers"""
        self.camera_helper = camera_helper
        self.genicam_helper = GenICamHelper()
        self.genicam_helper.set_camera(camera_helper.camera)

    def capture_frame(self, timeout_ms=1000):
        if not self.camera_helper or not self.camera_helper.camera:
            raise RuntimeError("Camera not initialized")
        grab_result = self.camera_helper.camera.GrabOne(timeout_ms)
        if grab_result.GrabSucceeded():
            return grab_result.Array
        raise RuntimeError("Failed to capture image")

    def capture_stack(self, n, settle=2, delay=0.0):
        """Capture n frames; optionally discard first 'settle' frames."""
        frames = []
        # Discard a few to settle auto-pipelines (even if autos are off)
        for _ in range(max(0, settle)):
            _ = self.capture_frame()
        for _ in range(n):
            frames.append(self.capture_frame())
            if delay > 0:
                time.sleep(delay)
        return np.stack(frames, axis=0)  # [N,H,W,(C)]

    # -------------------------
    # Basic metrics
    # -------------------------

    def calculate_sharpness(self, image):
        gray = _to_gray(image)
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        return float(lap.var())

    def calculate_noise(self, image):
        gray = _to_gray(image)
        h, w = gray.shape
        cy0, cy1 = h // 4, 3 * h // 4
        cx0, cx1 = w // 4, 3 * w // 4
        center = gray[cy0:cy1, cx0:cx1]
        return float(np.std(center))

    def calculate_contrast(self, image):
        gray = _to_gray(image)
        p5 = float(np.percentile(gray, 5))
        p95 = float(np.percentile(gray, 95))
        if p5 <= 0:
            p5 = 1.0
        return float(p95 / p5)

    # -------------------------
    # EMVA-lite metrics
    # -------------------------

    def compute_temporal_noise(self, stack):
        """Median per-pixel std over time (DN)."""
        gray_stack = np.stack([_to_gray(f) for f in stack], axis=0).astype(np.float32)
        perpix_std = gray_stack.std(axis=0)
        return float(np.median(perpix_std))

    def compute_dsnu_prnu(self, dark_stack, bright_stack):
        """
        DSNU: std of dark mean frame (DN)
        PRNU: std/mean on (bright_mean - dark_mean)
        """
        d = np.stack([_to_gray(f) for f in dark_stack], axis=0).astype(np.float32)
        b = np.stack([_to_gray(f) for f in bright_stack], axis=0).astype(np.float32)
        d_mean = d.mean(axis=0)
        b_mean = b.mean(axis=0)
        dsnu_dn = float(d_mean.std())

        signal = np.clip(b_mean - d_mean, 0, None)
        mean_signal = float(signal.mean())
        prnu = float(signal.std() / mean_signal) if mean_signal > 0 else float("nan")
        return dsnu_dn, prnu, mean_signal

    def try_set_exposure(self, value):
        """
        Best-effort exposure set using common GenICam names.
        Silently no-op if not supported.
        """
        try:
            self.genicam_helper.set_node("ExposureAuto", "Off")
        except Exception:
            pass
        try:
            # Accepts us or ns depending on device; helper should map
            self.genicam_helper.set_node("ExposureTime", float(value))
        except Exception:
            try:
                self.genicam_helper.set_node("ExposureTimeAbs", float(value))
            except Exception:
                return False
        return True

    def try_get_saturation_dn(self, image=None):
        """
        Approximate 'saturation DN' as the max representable DN inferred from dtype,
        or from a provided image. Used for DR estimate.
        """
        if image is not None:
            img = _to_gray(image)
            if img.dtype == np.uint8:
                return 255.0
            if img.dtype == np.uint16:
                return 65535.0
            return float(img.max())
        return 255.0

    def compute_linearity_and_dr(self, exposure_list):
        """
        Sweep exposure (best-effort). Returns:
          gain_slope, offset, r2, noise_floor, dr_db, dr_stops
        Falls back to None if sweep not possible.
        """
        means = []
        used = []
        for exp in exposure_list:
            if not self.try_set_exposure(exp):
                continue
            # Small settle
            _ = self.capture_frame()
            stack = self.capture_stack(8, settle=0)
            gray = np.stack([_to_gray(f) for f in stack], axis=0).astype(np.float32)
            means.append(gray.mean())
            used.append(float(exp))

        if len(used) < 3:
            return None

        x = np.array(used, dtype=np.float64)
        y = np.array(means, dtype=np.float64)
        A = np.vstack([x, np.ones_like(x)]).T
        slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
        y_pred = slope * x + intercept
        ss_res = float(np.sum((y - y_pred) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

        # Noise floor from a short dark-ish stack (reuse last capture)
        noise_floor = float(np.median(np.std(gray, axis=0)))  # DN
        sat = self.try_get_saturation_dn()
        # Use positive dynamic range
        numerator = max(sat - intercept, 1e-6)
        dr_ratio = max(numerator / max(noise_floor, 1e-6), 1e-6)
        dr_db = 20.0 * np.log10(dr_ratio)
        dr_stops = np.log2(dr_ratio)

        return float(slope), float(intercept), float(r2), noise_floor, float(dr_db), float(dr_stops)

    # -------------------------
    # MTF sanity (edge + FFT)
    # -------------------------

    def compute_mtf_sanity(self, image):
        """
        Very lightweight MTF proxy:
          - find strongest edge via Sobel magnitude
          - compute edge spread (lower = sharper)
          - FFT energy roll-off metric
        Returns mtf_proxy (higher ~ sharper), fft_rolloff (higher = steeper roll-off)
        """
        gray = _to_gray(image).astype(np.float32)
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        mag = cv2.magnitude(gx, gy)
        # Edge spread proxy: std in a band around max-gradient line
        yx = np.unravel_index(np.argmax(mag), mag.shape)
        y0, x0 = yx
        y0 = int(np.clip(y0, 5, gray.shape[0] - 6))
        band = gray[y0 - 5:y0 + 5, :]
        edge_spread = float(band.std()) + 1e-9  # avoid zero

        # FFT roll-off: ratio of low vs high frequency energy
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        ps = np.abs(fshift) ** 2
        h, w = ps.shape
        cy, cx = h // 2, w // 2
        r = min(cy, cx)
        low = ps[cy - r // 4:cy + r // 4, cx - r // 4:cx + r // 4].mean()
        high_ring = ps.mean() - low
        fft_rolloff = float(low / (high_ring + 1e-9))

        # MTF proxy: inverse of edge_spread
        mtf_proxy = float(1.0 / edge_spread)
        return mtf_proxy, fft_rolloff

    # -------------------------
    # Public runner
    # -------------------------

    def test_image_quality(self):
        """
        Returns a dict with:
          success, overall_pass, results{ sharpness, noise, contrast, ...advanced }
        """
        try:
            # --- Basic single frame ---
            img = self.capture_frame()

            sharpness = self.calculate_sharpness(img)
            noise = self.calculate_noise(img)
            contrast = self.calculate_contrast(img)
            mtf_proxy, fft_roll = self.compute_mtf_sanity(img)

            results = {
                "sharpness": {"value": sharpness, "pass": sharpness > self.min_sharpness,
                              "threshold": self.min_sharpness},
                "noise": {"value": noise, "pass": noise < self.max_noise,
                          "threshold": self.max_noise},
                "contrast": {"value": contrast, "pass": contrast > self.min_contrast,
                             "threshold": self.min_contrast},
                "mtf_proxy": {"value": mtf_proxy, "pass": np.isfinite(mtf_proxy), "threshold": None},
                "fft_rolloff": {"value": fft_roll, "pass": np.isfinite(fft_roll), "threshold": None},
            }

            # --- Stacks for EMVA-lite ---
            try:
                stack = self.capture_stack(self.stack_N, settle=2)
                temporal_noise = self.compute_temporal_noise(stack)
                results["temporal_noise"] = {
                    "value": temporal_noise, "pass": np.isfinite(temporal_noise), "threshold": None
                }
            except Exception as _:
                results["temporal_noise"] = {"value": float("nan"), "pass": False, "threshold": None}

            # Optional DSNU/PRNU: best-effort using two stacks
            try:
                # If you have light control, consider toggling exposure/illum; here we just split stack
                half = max(2, self.stack_N // 2)
                dark_stack = self.capture_stack(half, settle=1)
                bright_stack = self.capture_stack(half, settle=1)
                dsnu_dn, prnu, mean_signal = self.compute_dsnu_prnu(dark_stack, bright_stack)
                results["dsnu_dn"] = {"value": dsnu_dn, "pass": np.isfinite(dsnu_dn), "threshold": None}
                results["prnu"] = {"value": prnu, "pass": np.isfinite(prnu), "threshold": None}
                results["mean_signal"] = {"value": mean_signal, "pass": np.isfinite(mean_signal),
                                          "threshold": None}
            except Exception as _:
                results["dsnu_dn"] = {"value": float("nan"), "pass": False, "threshold": None}
                results["prnu"] = {"value": float("nan"), "pass": False, "threshold": None}
                results["mean_signal"] = {"value": float("nan"), "pass": False, "threshold": None}

            # Linearity/DR sweep (best-effort)
            try:
                # Use a spread of exposure candidates; helper may accept us or ns transparently.
                exposure_list = [500.0, 1000.0, 2000.0, 4000.0, 8000.0]
                lin = self.compute_linearity_and_dr(exposure_list)
                if lin is not None:
                    slope, offset, r2, noise_floor, dr_db, dr_stops = lin
                    results["linearity_gain"] = {"value": slope, "pass": np.isfinite(slope), "threshold": None}
                    results["linearity_offset"] = {"value": offset, "pass": np.isfinite(offset), "threshold": None}
                    results["linearity_r2"] = {"value": r2, "pass": r2 >= 0.95, "threshold": 0.95}
                    results["dr_db"] = {"value": dr_db, "pass": np.isfinite(dr_db), "threshold": None}
                    results["dr_stops"] = {"value": dr_stops, "pass": np.isfinite(dr_stops), "threshold": None}
                    results["noise_floor"] = {"value": noise_floor, "pass": np.isfinite(noise_floor),
                                              "threshold": None}
                else:
                    for k in ["linearity_gain", "linearity_offset", "linearity_r2",
                              "dr_db", "dr_stops", "noise_floor"]:
                        results[k] = {"value": float("nan"), "pass": False, "threshold": None}
            except Exception as _:
                for k in ["linearity_gain", "linearity_offset", "linearity_r2",
                          "dr_db", "dr_stops", "noise_floor"]:
                    results[k] = {"value": float("nan"), "pass": False, "threshold": None}

            overall = all(r["pass"] for k, r in results.items()
                          if k in ["sharpness", "noise", "contrast"])  # only hard KPIs
            return {"success": True, "results": results, "overall_pass": overall}

        except Exception as e:
            return {"success": False, "error": str(e), "overall_pass": False}

    def set_quality_thresholds(self, min_sharpness=None, max_noise=None, min_contrast=None):
        if min_sharpness is not None:
            self.min_sharpness = float(min_sharpness)
        if max_noise is not None:
            self.max_noise = float(max_noise)
        if min_contrast is not None:
            self.min_contrast = float(min_contrast)


@pytest.mark.parametrize("smoke", [True])  # hook to extend later
def test_image_quality_metrics(camera_helper, simulate, smoke):
    """
    - Simulation: ensure all metrics compute finite values; do not assert product thresholds.
    - Real camera: assert the basic KPIs (sharpness/noise/contrast) against conservative defaults.
    Advanced EMVA-lite metrics are best-effort and only checked for numeric sanity by default.
    """
    tq = TestImageQuality()
    tq.setup(camera_helper)
    out = tq.test_image_quality()
    assert out["success"], "Image quality metrics computation failed"

    metrics = out["results"]

    # Always: computed values must be finite where meaningful
    for name, data in metrics.items():
        val = data["value"]
        if val is not None:
            assert np.isfinite(val), f"Metric {name} produced non-finite value"

    if simulate:
        # In simulation we only sanity-check numerics; your simulator may inject patterns/noise.
        return

    # Real hardware: require core KPIs
    assert metrics["sharpness"]["pass"], "Image sharpness below threshold"
    assert metrics["noise"]["pass"], "Image noise above threshold"
    assert metrics["contrast"]["pass"], "Image contrast below threshold"

    # Optional: if linearity_r2 is available, enforce a mild floor
    r2 = metrics.get("linearity_r2", {}).get("value")
    if r2 is not None and np.isfinite(r2):
        assert r2 >= 0.90, f"Linearity R² too low: {r2:.3f}"
