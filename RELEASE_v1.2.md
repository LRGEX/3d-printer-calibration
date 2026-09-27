# 🎯 3D Printer Calibration Utility v1.2

**Release Date:** May 25, 2025  
**Author:** LRGEX

## 🚀 What's New in v1.2

### ✨ **Core Features**
- **E-steps Calibration** for Marlin firmware
- **Rotation Distance Calibration** for Klipper firmware  
- **Flow Ratio Calibration** with dual methods (OrcaSlicer + Manual)
- **Axis Calibration** for X, Y, Z dimensions

### 🔧 **Key Improvements**
- ✅ **Fixed calculation formulas** across all calibration types
- 🎨 **Enhanced UI** with colorful output using Colorama
- 📏 **Dynamic measurement** - automatically calculates filament measurement length
- 🔄 **Simplified workflow** with clear step-by-step instructions

### 🛠️ **Technical Enhancements**
- **Corrected E-steps formula**: `new_esteps = old_esteps * (actual_extruded / 100)`
- **Fixed rotation distance formula**: `new_rot_distance = old_rotation_distance * (actual_extruded / expected_extrusion)`
- **Improved axis calibration formula**: `new_distance = current_distance * (measured / expected)`
- **Better flow ratio calculations** for both OrcaSlicer and manual methods

### 💡 **User Experience**
- **Color-coded interface** for better readability
- **Clear prompts** with example values
- **Automatic timing** for result display
- **Support for both firmware types** (Marlin & Klipper)

---

## 📦 **Quick Start**

```bash
# Install dependencies
pip install colorama

# Run the application
python app.py
```

## 🎯 **Perfect For**
- 3D printer enthusiasts
- Both Marlin and Klipper users
- Anyone needing accurate calibration tools
- Beginners and experts alike

---

**Download now and get your 3D printer perfectly calibrated! 🎉**
