# 🔧 3D Printer Calibration Utility

**Author:** LRGEX  
**Latest Version:** v2.0.3  
**Requires:** Python 3.10+

A comprehensive calibration tool for 3D printers supporting both **Marlin** and **Klipper** firmware. This utility helps you calibrate E-steps, rotation distances, flow ratios, and axis movements with enhanced user experience and robust input validation.

## ✨ Features

### 🎯 Calibration Types
- **E-steps Calibration (Marlin)**: Calibrate extruder steps per millimeter
- **Rotation Distance Calibration (Klipper)**: Calibrate extruder rotation distance  
- **Flow Ratio Calibration (Klipper)**: Fine-tune extrusion flow with two methods:
  - OrcaSlicer Flow Rate calibration results
  - Manual wall thickness measurement
- **Axis Calibration (Klipper)**: Calibrate X, Y, Z axis rotation distances
- **Dimensional Accuracy (OrcaSlicer)**: Two-square + holes method that computes Shrinkage (XY), X-Y contour compensation and X-Y hole compensation, with per-filament history and a verify mode

### 🎨 Enhanced User Experience
- **Step-by-step guidance**: Clear progress indicators (Step 1/4, 2/4, etc.)
- **Color-coded interface**: Beautiful terminal colors with emoji indicators
- **Crystal clear instructions**: Exact printer.cfg locations and common values
- **User-controlled pacing**: Press Enter prompts instead of forced delays
- **Comprehensive help system**: Built-in guidance and calibration tips
- **Input validation**: Robust error handling with helpful error messages
- **Actionable results**: Copy-paste ready configuration snippets

### 🎯 Perfect For
- 3D printer enthusiasts and professionals
- Both Marlin and Klipper users
- Anyone needing accurate calibration tools
- Beginners and experts alike

---

## 📋 Changelog

### 🔧 Version 2.0.3 - *Test Restoration & Cleanup*

#### 🧪 Testing
- **Restored the Dimensional Accuracy test suite** as `tests/test_dimcal.py` (26 tests): axis fit (spec case, perfect print, pure offset, pure scale), OrcaSlicer conversion, hole compensation, square/bed/hole validation, hole row layout centers, setup-store migration (v2.0.1 legacy flat files) with malformed-entry handling, and duplicate-hole detection
- Full suite now **43 tests**, verified green on Python 3.10 and 3.12

#### 🛠️ Fixes
- **Stale docstring** in `dimcal_measure()` corrected: bounds are now documented as "squares +/-3%, holes +/- max(0.5mm, 10%)"
- **Z override no longer duplicates the formula** - both the guarded calculator and the manual override call the single pure `z_rotation_distance_raw()` function

---

### 🔧 Version 2.0.2 - *Compatibility & Robustness Release*

#### 🐛 Bug Fixes
- **Fixed SyntaxError on Python 3.10/3.11** - backslash inside an f-string expression (verify-status line) moved to a variable; `py_compile` verified on 3.10, 3.11, 3.12 and 3.13. Project now officially supports **Python 3.10+**
- **Hole measurement bounds relaxed** - holes now accept nominal +/- max(0.5mm, 10%) instead of the 3% used for squares (a normal 2.8mm reading on a 3mm hole is no longer rejected)
- **Z 2% guard no longer hard-blocks** - corrections above 2% show the warning, then offer "Use this value anyway? (y/n)"; `y` applies the value, `n` re-measures
- **Calibration data files now live next to the app** (or next to the .exe when frozen) instead of the current working directory
- **Setups are stored per filament** (dict keyed by filament name, never overwritten across filaments); measure/verify lets you pick which filament setup to use when several are saved; v2.0.1 legacy flat setup files are migrated automatically

#### 🛠️ Technical
- New pure function `measurement_bounds(nominal, hole)` drives all measurement input limits
- New helpers `_load_setups()` / `_pick_setup()` with legacy-file migration
- Test suite recreated in `tests/test_app.py` (17 tests): formulas, extrusion bounds, Z guard, hole bounds (3mm accepts 2.8), and scripted Z confirm/negate paths
- `requirements.txt` added (colorama, loguru); header date 2026-09-27; version 2.0.2

---

### 🔧 Version 2.0.1 - *Bug Fix Release*

#### 🐛 Bug Fixes
- **Fixed crash: division by zero in E-steps calibration** - leftover equal to the marked length (no filament moved) now shows a clear red error and re-asks instead of killing the program
- **Fixed silent bad result in Rotation Distance calibration** - the same shared validation now prevents the dangerous `rotation_distance: 0.0000` output
- **Replaced single-cube X/Y axis calibration** with **Z Rotation Distance (Lead Screw)** calibration: X/Y belt axes use the mechanical value (belt pitch x pulley teeth); X/Y dimension errors are flagged as slicer/flow issues; Z requires a tall test (>= 50mm), warns about first-layer/Z offset influence, and rejects corrections above 2% as likely mechanical problems
- **Removed hardcoded input limits** - extruder rotation distance bound is now the named `MAX_EXTRUDER_ROTATION_DISTANCE` constant; all other bounds moved to constants (flow modifier, wall thickness, extrusion/marked lengths, Z test height)
- **`MEASUREMENT_LENGTH` is no longer dead code** - it is now the default (120mm) for the marked-length prompts
- **Removed the double prompt** after every calibration - now a single "Press Enter" returns to the menu (Exit lives in the menu)
- **Flow Ratio correctly labeled (Slicer)** instead of (Klipper) in menu, headers, docstrings and help; added a "How to apply" section (Filament settings -> Flow ratio) and a note that calipers compress single walls (OrcaSlicer method is more reliable)
- **Help text updated** to match the Z-only calibration and slicer flow ratio
- **Top-level crash handler now prints the full traceback** (`traceback.print_exc()`) so bugs are reportable

#### 🛠️ Technical
- All formulas extracted into pure, unit-tested functions: `calc_esteps`, `calc_rotation_distance`, `calc_flow_ratio_orca`, `calc_flow_ratio_wall`, `calc_z_rotation_distance`, plus the shared `validate_actual_extruded` helper
- New test suite `tests/test_app.py` (18 tests): spec formula values, 50-150% extrusion bounds, 2% Z guard (with float epsilon for the exact boundary), and scripted-input subprocess repros proving the program survives and re-asks. *(Test files later removed from the repo at maintainer's request - the formula functions remain pure and re-testable at any time.)*
- Version bumped to 2.0.1 in logo and docs

---

### 🚀 Version 2.1 - *Dimensional Accuracy Edition*

#### 🎯 New Features
- **Dimensional Accuracy Calibration (OrcaSlicer)**: full workflow for the Elegoo Centauri Carbon (CC1)
  - Interactive setup wizard with defaults (PCTG, 30/100mm squares, holes ⌀20 + ⌀3/5/10/20)
  - Validation: large ≥ 3× small, 256×256 bed fit with 10mm gap, 5mm hole walls/spacing, holes ≥ 2mm
  - Build sheet output (user creates the two squares in their own CAD) with high-quality circle export guidance
  - Measurement entry with ±3% bounds, per-axis slope/offset model
  - OrcaSlicer outputs with exact menu locations: Shrinkage (XY), X-Y contour compensation, X-Y hole compensation
  - Warnings: X/Y slope mismatch (belt tension), abnormal slope, hole compensation spread, duplicate-diameter mismatch
  - Per-filament JSON history (`dimcal_history.json`, appended, never overwritten)
  - Verify mode: reprint check, PASS when all residuals within ±0.1mm

#### 🛠️ Technical Improvements
- **Unit test suite** (`test_dimcal.py`, 29 tests via pytest): math spec cases, perfect-print case, all validation rejections, hole row layout
- **Structured logging** via loguru for file operations (setup save/load, history)
- **Persistence**: setup + history stored as UTF-8 JSON via pathlib context managers
- **Dependency**: added `loguru` (runtime) and `pytest` (dev)

#### 📦 Installation Options
```bash
# Option 1: Standalone Executable
# Download 3D-Printer-Calibration exe and run directly

# Option 2: From Source
uv sync
python app.py
```

---

### 🚀 Version 2.0 - *Advanced Edition*

#### 🎯 New Features
- **Standalone Executable**: No Python installation required - runs on any Windows system
- **Modern Package Management**: Uses `uv` instead of pip for faster, reliable dependency management
- **Enhanced Input Validation**: `get_float_input()` with min/max values and zero/negative handling
- **Comprehensive Error Handling**: Try/catch blocks with user-friendly messages
- **Professional Distribution**: PyInstaller executable with LRGEX branding
- **Deviation Warnings**: Alerts for large calibration changes

#### 🛠️ Technical Improvements
- **Build System**: PyInstaller with custom icons and metadata
- **Self-contained Application**: All dependencies bundled inside executable
- **Code Quality**: Comprehensive docstrings, constants, and clean code structure

#### 📦 Installation Options
```bash
# Option 1: Standalone Executable (Recommended)
# Download 3D-Printer-Calibration exe and run directly

# Option 2: From Source
uv sync
python app.py

# Option 3: Build Your Own
pyinstaller --onefile --console --icon="path/to/icon.ico" --name="3D-Printer-Calibration-v2.0.3" app.py
```

---

### ✨ Version 1.2 - *Initial Release*
**Release Date:** June 15, 2024

#### 🎯 Features Added
- **E-steps Calibration** for Marlin firmware
- **Rotation Distance Calibration** for Klipper firmware  
- **Flow Ratio Calibration** with dual methods (OrcaSlicer + Manual)
- **Axis Calibration** for X, Y, Z dimensions

#### 🛠️ Technical Implementation
- **Fixed calculation formulas** across all calibration types
- **Color-coded interface** using Colorama
- **Dynamic measurement calculations**
- **Step-by-step workflow** with clear instructions

#### 📦 Installation
```bash
# Install dependencies
pip install colorama

# Run the application
python app.py
```

---

## 📖 Usage Guide

### 🎯 Calibration Order Recommendations
1. **Start with E-steps/Rotation Distance** - Get basic extrusion correct
2. **Then Flow Ratio calibration** - Fine-tune extrusion amount  
3. **Finally Axis calibration** - Ensure dimensional accuracy

### ⚠️ Important Notes
- Always heat your hotend before extruder calibrations
- Use the same filament type you normally print with
- Ensure your printer is mechanically sound before calibrating
- Backup your current settings before making changes
- Test with a small print after each calibration

---

**Happy Printing! 🎯✨**
