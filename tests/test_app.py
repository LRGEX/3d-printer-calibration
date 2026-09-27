#!/usr/bin/env python3
"""
Unit + scripted-input tests for v2.0.1/v2.0.2 fixes.

v2.0.1: pure formulas, extrusion bounds, Z guard
v2.0.2: hole measurement bounds, Z confirm-override path, multi-Python safety
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from app import (
    calc_esteps,
    calc_flow_ratio_orca,
    calc_flow_ratio_wall,
    calc_rotation_distance,
    calc_z_rotation_distance,
    measurement_bounds,
    validate_actual_extruded,
)

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


# ---------- v2.0.1 formula functions ----------

class TestFormulas:
    def test_esteps(self):
        assert calc_esteps(93, 100, 97.42) == pytest.approx(95.46)

    def test_rotation_distance(self):
        assert calc_rotation_distance(7.71, 100, 97.42) == pytest.approx(7.5111)

    def test_flow_orca(self):
        assert calc_flow_ratio_orca(0.96, 5) == pytest.approx(1.008)

    def test_flow_wall(self):
        assert calc_flow_ratio_wall(0.96, 0.4, 0.36) == pytest.approx(1.0667)


# ---------- v2.0.1 extrusion validation ----------

class TestExtrusionValidation:
    def test_zero_actual_raises_value_error(self):
        with pytest.raises(ValueError):
            calc_esteps(93, 100, 0)

    def test_zero_actual_rotation_raises_value_error(self):
        with pytest.raises(ValueError):
            calc_rotation_distance(7.71, 100, 0)

    def test_below_50_percent_rejected(self):
        with pytest.raises(ValueError):
            calc_esteps(93, 100, 49.9)

    def test_above_150_percent_rejected(self):
        with pytest.raises(ValueError):
            calc_esteps(93, 100, 150.1)

    def test_validator_returns_reason_string(self):
        assert validate_actual_extruded(0, 100) is not None
        assert validate_actual_extruded(100, 100) is None


# ---------- v2.0.1 Z guard ----------

class TestZRotationValidation:
    def test_small_correction_accepted(self):
        assert calc_z_rotation_distance(8.0, 100.0, 100.5) == pytest.approx(8.04)

    def test_correction_above_2_percent_raises(self):
        with pytest.raises(ValueError):
            calc_z_rotation_distance(8.0, 100.0, 105.0)  # 5%


# ---------- v2.0.2 hole measurement bounds ----------

class TestHoleMeasurementBounds:
    def test_3mm_hole_accepts_2_8(self):
        lo, hi = measurement_bounds(3.0, hole=True)
        assert lo == pytest.approx(2.5)
        assert hi == pytest.approx(3.5)
        assert lo <= 2.8 <= hi  # normal print result, must be accepted

    def test_20mm_hole_uses_10_percent(self):
        lo, hi = measurement_bounds(20.0, hole=True)
        assert lo == pytest.approx(18.0)
        assert hi == pytest.approx(22.0)

    def test_small_hole_floor_is_0_5mm(self):
        lo, hi = measurement_bounds(2.0, hole=True)  # 10% = 0.2 < 0.5 floor
        assert lo == pytest.approx(1.5)
        assert hi == pytest.approx(2.5)

    def test_squares_keep_3_percent(self):
        lo, hi = measurement_bounds(30.0)
        assert lo == pytest.approx(29.1)
        assert hi == pytest.approx(30.9)


# ---------- v2.0.2 Z confirm-override (scripted) ----------

class TestZConfirmOverride:
    def test_5_percent_with_y_confirmation_returns_value(self):
        # 4 -> Z cal, 8 -> current rd, 100 -> expected, 105 -> measured (5%),
        # y -> use anyway, "" -> continue, 7 -> exit
        inputs = "\n".join(["4", "8", "100", "105", "y", "", "7"]) + "\n"
        result = subprocess.run(
            [sys.executable, str(APP_PATH)],
            input=inputs, capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONUTF8": "1"},
        )
        out = result.stdout
        assert result.returncode == 0, out + result.stderr
        assert "Use this value anyway? (y/n)" in out   # escape hatch offered
        assert "8.4000" in out                          # 8 * 105/100 accepted

    def test_5_percent_with_n_remeasures(self):
        inputs = "\n".join(["4", "8", "100", "105", "n", "100.5", "", "7"]) + "\n"
        result = subprocess.run(
            [sys.executable, str(APP_PATH)],
            input=inputs, capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONUTF8": "1"},
        )
        out = result.stdout
        assert result.returncode == 0, out + result.stderr
        assert "Use this value anyway? (y/n)" in out
        assert "8.0400" in out                          # 8 * 100.5/100
