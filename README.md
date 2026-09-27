# 🔧 3D Printer Calibration Utility

**Author:** LRGEX · **Version:** v2.0.3 · **Requires:** Python 3.10+ (exe: no Python needed) · **License:** MIT

A console calibration suite for FDM printers running **Marlin**, **Klipper** or any slicer — with a math-driven **Dimensional Accuracy** wizard for OrcaSlicer that computes your compensation values in one pass instead of trial and error.

## Why this exists

OrcaSlicer ships the test model and the settings — **Shrinkage (XY)**, **X-Y hole compensation**, **X-Y contour compensation** — but no math. The official workflow is: print the tolerance test, measure, tweak the settings, *"repeat the process until you achieve the desired precision."* The web calculators that exist cover one page each.

This is an **offline guided wizard** with **per-axis X/Y slope/offset separation**, **contour + hole outputs together**, **per-filament history** and a **verify loop**. The classic extruder calibrations (E-steps, rotation distance, flow ratio) ride along in the same menu.

| | OrcaSlicer built-in | Web calculators | This tool |
|---|---|---|---|
| E-steps / rotation distance math | ❌ | 🟡 some | ✅ |
| Flow ratio | ✅ (photo-analyzed) | 🟡 | ✅ (manual entry) |
| Dimensional: slope **and** offset separation | ❌ | ❌ | ✅ |
| Dimensional: contour **+** hole outputs | ❌ | 🟡 partial | ✅ |
| Per-filament history | ❌ | ❌ | ✅ |
| Verify loop (reprint → PASS ±0.1mm) | ❌ | ❌ | ✅ |
| Works offline | n/a | ❌ | ✅ |

*Honest note: the extruder basics are commodity — OrcaSlicer's built-in flow calibration (photo analysis) is easier than manual entry. The Dimensional Accuracy module is the reason this tool exists.*

## ✨ What's inside

### 📏 Dimensional Accuracy Calibration (OrcaSlicer) — the headline
- **Two-square + holes method**: printing one small (30mm) and one large (100mm) square separates *scale error* (shrinkage) from *constant error* (compensation) per axis — something a single test object cannot do
- Interactive setup wizard with validation: large ≥ 3× small, bed fit (256×256mm, Centauri Carbon), 5mm hole walls/spacing, holes ≥ 2mm
- Generates a **build sheet** (you create the two squares in any CAD; export circles at ≥128 segments)
- Guided measurement entry with sanity bounds (squares ±3%, holes ±max(0.5mm, 10%))
- Outputs the exact values with menu locations: **Filament → Shrinkage (XY)**, **Process → Quality → Precision → X-Y contour / X-Y hole compensation**
- Warnings for X/Y slope mismatch (belt tension), abnormal slope, hole spread, duplicate-diameter mismatch
- Setups and results stored **per filament** (JSON, appended — history never overwritten)
- **Verify mode**: reprint with the new values → residual per dimension → PASS if all within ±0.1mm

### 🔩 The classic calibrations
- **E-steps (Marlin)** — 5-step guided flow, guarded against bad measurements
- **Extruder rotation distance (Klipper)** — same guards, no silent zero results
- **Flow ratio (Slicer)** — from OrcaSlicer's flow calibration or wall-thickness measurement (with how-to-apply)
- **Z rotation distance (Klipper, lead screw)** — tall-test method with a 2% sanity guard; X/Y belt axes keep their mechanical value (belt pitch × pulley teeth)

Every formula lives in a pure, unit-tested function. Input validation everywhere: wrong entries are rejected with a reason, never crash the app.

## 📦 Installation

**Option 1 — Standalone executable (Windows, no Python needed):**
Download [`3D-Printer-Calibration-v2.0.3.exe`](https://github.com/LRGEX/3d-printer-calibration/releases/latest) from the releases page and run it. Calibration data files are saved next to the exe.

**Option 2 — From source with uv:**
```bash
uv sync
uv run python app.py
```

**Option 3 — From source with pip** (verified on a clean venv):
```bash
pip install -r requirements.txt   # colorama + loguru
python app.py
```

**Run the test suite (43 tests):**
```bash
uv sync
uv run pytest
```

**Build the exe yourself:**
```bash
build-executable.bat        # or: pyinstaller 3D-Printer-Calibration-v2.0.3.spec
```

## 📖 Usage

1. **E-steps / extruder rotation distance** — get basic extrusion right first
2. **Flow ratio** — fine-tune extrusion amount
3. **Z rotation distance** — only if Z height is off
4. **Dimensional Accuracy** — the final polish for print-perfect dimensions

⚠️ Heat the hotend before extruder calibrations · cool prints 30 minutes before measuring · back up your settings before changing them.

## 📄 License

[MIT](LICENSE) — © 2026 LRGEX

---

## 📋 Changelog

### v2.0.3 — Test Restoration & Cleanup
- Restored the Dimensional Accuracy test suite (`tests/test_dimcal.py`, 26 tests); full suite now **43 tests**, green on Python 3.10 and 3.12
- Z override path no longer duplicates the formula (single pure `z_rotation_distance_raw()`)
- Docstring fixes (measurement bounds wording)

### v2.0.2 — Compatibility & Robustness
- **Python 3.10+ support** (f-string backslash SyntaxError fixed; py_compile verified on 3.10–3.13)
- Hole measurement bounds relaxed to ±max(0.5mm, 10%); squares stay ±3%
- Z 2% guard now offers "use this value anyway?" instead of hard-blocking
- Data files saved next to the app/exe (not the working directory); setups stored per filament with picker; v2.0.1 flat files auto-migrate
- `requirements.txt` added

### v2.0.1 — Bug Fix Release
- Fixed crash (division by zero) and silent `rotation_distance: 0` on zero-extrusion input — validation re-asks instead
- Replaced single-cube X/Y axis calibration with **Z-only lead-screw** calibration (belt axes = mechanical value; >2% corrections rejected as likely mechanical)
- Flow ratio correctly labeled **(Slicer)** with how-to-apply; single-prompt menu flow; full traceback on unexpected errors
- All formulas extracted into pure, unit-tested functions

### v2.1 — Dimensional Accuracy Edition
- New **Dimensional Accuracy Calibration** module: setup wizard, build sheet, measurement entry, OrcaSlicer outputs, warnings, JSON history, verify mode
- Added loguru for file-operation logging

### v2.0 — Advanced Edition
- Standalone PyInstaller executable, uv package management, enhanced input validation

### v1.2 — Initial Release
- E-steps, rotation distance, flow ratio, cube-based axis calibration

---

**Happy printing! 🎯**
