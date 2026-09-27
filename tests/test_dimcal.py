#!/usr/bin/env python3
"""
Unit tests for the Dimensional Accuracy calibration math and validators (v2.0.3).

Covers: axis fit model (slope/offset), OrcaSlicer conversion, perfect/offset/
scale-only cases, hole compensation, square/bed/hole validation, hole row
layout, setup-store migration (legacy v2.0.1 flat files) and duplicate-hole
detection.
"""

import json

import pytest

import app
from app import (
    _find_dup_holes,
    _load_setups,
    dimcal_axis_fit,
    dimcal_hole_comp,
    dimcal_orca_values,
    layout_holes_row,
    validate_bed_fit,
    validate_holes,
    validate_square_sizes,
)


# ---------- Axis fit model ----------

class TestAxisFit:
    def test_spec_case(self):
        slope, offset = dimcal_axis_fit(20, 100, 19.8, 99.2)
        assert slope == pytest.approx(-0.0075)
        assert offset == pytest.approx(-0.05)

    def test_perfect_print(self):
        slope, offset = dimcal_axis_fit(30, 100, 30.0, 100.0)
        assert slope == pytest.approx(0.0)
        assert offset == pytest.approx(0.0)

    def test_pure_offset_only(self):
        # Same absolute error on both sizes -> zero slope, offset +0.2
        slope, offset = dimcal_axis_fit(30, 100, 30.2, 100.2)
        assert slope == pytest.approx(0.0)
        assert offset == pytest.approx(0.2)

    def test_pure_scale_only(self):
        # Purely proportional error -> slope, zero offset
        slope, offset = dimcal_axis_fit(30, 100, 29.91, 99.7)
        assert slope == pytest.approx(-0.003)
        assert offset == pytest.approx(0.0)


# ---------- OrcaSlicer conversion ----------

class TestOrcaValues:
    def test_spec_case(self):
        shrinkage, contour = dimcal_orca_values(-0.0075, -0.05)
        assert shrinkage == pytest.approx(99.25)
        assert contour == pytest.approx(0.025)

    def test_perfect_print(self):
        shrinkage, contour = dimcal_orca_values(0.0, 0.0)
        assert shrinkage == pytest.approx(100.0)
        assert contour == pytest.approx(0.0)

    def test_pure_offset_contour(self):
        _, contour = dimcal_orca_values(0.0, 0.2)
        assert contour == pytest.approx(-0.1)


# ---------- Hole compensation ----------

class TestHoleComp:
    def test_simple(self):
        assert dimcal_hole_comp(5, 4.8, 0) == pytest.approx(0.1)

    def test_scale_removed(self):
        assert dimcal_hole_comp(20, 19.94, -0.003) == pytest.approx(0.0)


# ---------- Square size validation ----------

class TestSquareValidation:
    def test_large_not_bigger_rejected(self):
        assert validate_square_sizes(100, 100) is not None
        assert validate_square_sizes(100, 50) is not None

    def test_large_below_3x_rejected(self):
        assert validate_square_sizes(30, 89) is not None

    def test_30_100_accepted(self):
        assert validate_square_sizes(30, 100) is None


# ---------- Bed fit validation ----------

class TestBedValidation:
    def test_30_100_accepted(self):
        assert validate_bed_fit(30, 100) is None

    def test_250_250_rejected(self):
        assert validate_bed_fit(250, 250) is not None

    def test_200_large_60_small_rejected(self):
        assert validate_bed_fit(60, 200) is not None


# ---------- Hole validation ----------

class TestHoleValidation:
    def test_below_2mm_rejected(self):
        assert validate_holes(100, [1.5]) is not None

    def test_hole_too_big_for_square_rejected(self):
        assert validate_holes(30, [25]) is not None

    def test_default_holes_accepted(self):
        assert validate_holes(100, [3, 5, 10, 20]) is None

    def test_too_many_holes_in_row_rejected(self):
        assert validate_holes(30, [10, 10, 10, 10]) is not None


# ---------- Hole row layout ----------

class TestHoleLayout:
    def test_default_hole_centers(self):
        assert layout_holes_row(100, [3, 5, 10, 20]) == [
            pytest.approx(25.0),
            pytest.approx(34.0),
            pytest.approx(46.5),
            pytest.approx(66.5),
        ]


# ---------- Setup store: legacy migration + malformed entries ----------

class TestLoadSetups:
    def test_legacy_flat_file_migrates_under_filament_key(self, tmp_path, monkeypatch):
        setup_file = tmp_path / "dimcal_setup.json"
        legacy = {
            "filament": "PCTG",
            "small": 30,
            "large": 100,
            "height": 5,
            "small_holes": [20],
            "large_holes": [3, 5, 10, 20],
        }
        setup_file.write_text(json.dumps(legacy), encoding="utf-8")
        monkeypatch.setattr(app, "DIMCAL_SETUP_FILE", setup_file)
        setups = _load_setups()
        assert list(setups.keys()) == ["PCTG"]
        assert setups["PCTG"]["small"] == 30

    def test_malformed_entries_dropped(self, tmp_path, monkeypatch):
        setup_file = tmp_path / "dimcal_setup.json"
        data = {
            "junk": 5,
            "also_junk": "not a setup",
            "PLA": {"filament": "PLA", "small": 30, "large": 100},
        }
        setup_file.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(app, "DIMCAL_SETUP_FILE", setup_file)
        setups = _load_setups()
        assert list(setups.keys()) == ["PLA"]
        assert isinstance(setups["PLA"], dict)

    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(app, "DIMCAL_SETUP_FILE", tmp_path / "nothing.json")
        assert _load_setups() == {}


# ---------- Duplicate-hole detection ----------

class TestFindDupHoles:
    SETUP = {
        "small_holes": [20.0],
        "large_holes": [20.0],
    }

    def test_difference_above_0_1_flagged(self):
        flagged = _find_dup_holes(self.SETUP, ms_holes=[19.90], ml_holes=[19.75])
        assert flagged and flagged[0][0] == pytest.approx(20.0)
        assert flagged[0][1] == pytest.approx(0.15)

    def test_difference_at_0_1_not_flagged(self):
        assert _find_dup_holes(self.SETUP, ms_holes=[19.90], ml_holes=[19.80]) == []

    def test_no_common_diameter_not_flagged(self):
        setup = {"small_holes": [10.0], "large_holes": [20.0]}
        assert _find_dup_holes(setup, ms_holes=[9.0], ml_holes=[19.0]) == []
