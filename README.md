# 🔧 3D Printer Calibration Utility

**Author:** LRGEX  
**Latest Version:** v2.0

A comprehensive calibration tool for 3D printers supporting both **Marlin** and **Klipper** firmware. This utility helps you calibrate E-steps, rotation distances, flow ratios, and axis movements with enhanced user experience and robust input validation.

## ✨ Features

### 🎯 Calibration Types
- **E-steps Calibration (Marlin)**: Calibrate extruder steps per millimeter
- **Rotation Distance Calibration (Klipper)**: Calibrate extruder rotation distance  
- **Flow Ratio Calibration (Klipper)**: Fine-tune extrusion flow with two methods:
  - OrcaSlicer Flow Rate calibration results
  - Manual wall thickness measurement
- **Axis Calibration (Klipper)**: Calibrate X, Y, Z axis rotation distances

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
# Download 3D-Printer-Calibration-v2.0.exe and run directly

# Option 2: From Source
uv sync
python app.py

# Option 3: Build Your Own
pyinstaller --onefile --console --icon="path/to/icon.ico" --name="3D-Printer-Calibration-v2.0" app.py
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
