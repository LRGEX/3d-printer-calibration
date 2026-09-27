"""
3D Printer Calibration Utility

This utility provides calibration tools for 3D printers using both Marlin and Klipper firmware.
It includes calibration for E-steps, extruder and Z lead-screw rotation distances,
slicer flow ratio, and dimensional accuracy (shrinkage / contour / hole compensation
for OrcaSlicer).

Features:
- Input validation with clear error messages
- Support for both Marlin and Klipper firmware
- Multiple calibration methods for flow ratio
- Color-coded output for better user experience

Author: LRGEX
Version: 2.0.3
Date: 2026-09-27
License: MIT License

"""

import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

from colorama import Fore, Style, init
from loguru import logger

# Initialize colorama (Fixes Windows CMD issues)
init(autoreset=True)

# Configure logger (level + message only, colored)
logger.remove()
logger.add(sys.stderr, format="<level>{level}</level> | {message}", colorize=True)

# Robust emoji output even when stdout is redirected (legacy Windows codepages)
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Constants
CONTINUE_PROMPT = "\nPress Enter to continue..."
DEFAULT_EXTRUSION_LENGTH = 100.0
MEASUREMENT_LENGTH = 120.0
MIN_ESTEPS = 1.0
MAX_ESTEPS = 10000.0
MIN_ROTATION_DISTANCE = 0.1
MAX_ROTATION_DISTANCE = 100.0
MAX_EXTRUDER_ROTATION_DISTANCE = 50.0   # extruder-specific upper bound
MIN_FLOW_RATIO = 0.1
MAX_FLOW_RATIO = 2.0
MIN_FLOW_MODIFIER = -50.0
MAX_FLOW_MODIFIER = 50.0
MIN_WALL_THICKNESS = 0.05
MAX_WALL_THICKNESS = 5.0
MIN_EXTRUSION_LENGTH = 10.0
MAX_EXTRUSION_LENGTH = 200.0
MAX_MARKED_LENGTH = 1000.0
ACTUAL_MIN_RATIO = 0.5    # actual extruded must be >= 50% of expected
ACTUAL_MAX_RATIO = 1.5    # actual extruded must be <= 150% of expected
MIN_Z_TEST_HEIGHT = 50.0  # Z calibration requires a tall test print
MAX_Z_DIMENSION = 500.0
MAX_Z_CORRECTION = 0.02   # Z corrections above this warn (with override option)
HOLE_MEAS_TOLERANCE_MM = 0.5   # holes: nominal +/- max(0.5mm, 10%)

# Dimensional Accuracy calibration constants
BED_MAX_X = 256.0                 # Elegoo Centauri Carbon bed
BED_MAX_Y = 256.0
BED_GAP_MIN = 10.0                # min gap between the two squares on the plate
HOLE_MARGIN = 5.0                 # min wall between holes / to square edges
HOLE_MIN_DIAMETER = 2.0
SIZE_RATIO_MIN = 3.0              # large square >= 3x small (slope math reliability)
MEAS_TOLERANCE = 0.03            # measurements must be within +/-3% of nominal
AXIS_MISMATCH_WARN = 0.001       # |slopeX - slopeY| > 0.1% -> belt/mechanical issue
SLOPE_ABNORMAL_WARN = 0.008      # |slope_avg| > 0.8% -> check belts/steps first
HOLE_SPREAD_WARN = 0.05          # per-hole comp max-min > 0.05mm -> polyholes advice
HOLE_DUP_DIFF_WARN = 0.1         # same diameter in both squares differs > 0.1mm
VERIFY_TOLERANCE = 0.1           # verify mode: PASS if all residuals <= +/-0.1mm
DEFAULT_FILAMENT = "PCTG"
DEFAULT_SMALL_SQUARE = 30.0
DEFAULT_LARGE_SQUARE = 100.0
DEFAULT_HEIGHT = 5.0
DEFAULT_SMALL_HOLES = [20.0]
DEFAULT_LARGE_HOLES = [3.0, 5.0, 10.0, 20.0]
# Data files live next to the app (or the .exe when frozen), never the CWD
APP_DATA_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
DIMCAL_SETUP_FILE = APP_DATA_DIR / "dimcal_setup.json"
DIMCAL_HISTORY_FILE = APP_DATA_DIR / "dimcal_history.json"



def get_menu_choice(valid_choices):
    """
    Get a validated menu choice from the user.
    
    Args:
        valid_choices (list): List of valid choice strings
    
    Returns:
        str: The validated choice
    """
    while True:
        choice = input(f"Enter your choice ({'/'.join(valid_choices)}): ").strip()
        if choice in valid_choices:
            return choice
        print(f"❌ Invalid choice. Please select {', '.join(valid_choices)}.")


def get_float_input(prompt, min_value=0.001, max_value=1000.0, allow_zero=False, allow_negative=False, default=None):
    """
    Get a validated float input from the user.
    
    Args:
        prompt (str): The input prompt to display
        min_value (float): Minimum allowed value
        max_value (float): Maximum allowed value
        allow_zero (bool): Whether to allow zero values
        allow_negative (bool): Whether to allow negative values
        default (float): Default value if user enters nothing
    
    Returns:
        float: The validated float value
    """
    while True:
        try:
            value = input(prompt).strip()
            if not value:
                if default is not None:
                    return default
                print("❌ Please enter a value.")
                continue
            
            num = float(value)
            
            if not allow_zero and num == 0:
                print("❌ Value cannot be zero.")
                continue
            elif not allow_negative and num < 0:
                print("❌ Value cannot be negative.")
                continue
            elif num < min_value or num > max_value:
                print(f"❌ Value must be between {min_value} and {max_value}.")
                continue
                
            return num
        except ValueError:
            print("❌ Please enter a valid number.")


def validate_actual_extruded(actual: float, expected: float) -> str | None:
    """
    Validate the actually extruded length before using it in a formula.

    Synopsis: Rejects zero/negative extrusion (extruder skipped, hotend
        cold) and values outside 50-150% of the expected amount (wrong
        marks or typo) - both would produce garbage calibration values.
    Parameters: Actual and expected extruded lengths in mm.
    Returns: None if valid, otherwise the rejection reason.
    """
    if actual <= 0:
        return ("Leftover equals the marked length - no filament moved. "
                "Did the extruder skip or is the hotend too cold?")
    if actual < ACTUAL_MIN_RATIO * expected:
        return (f"Only {actual:.2f}mm of {expected:.0f}mm expected moved "
                f"(< {ACTUAL_MIN_RATIO * 100:.0f}%). Check your marks and measurements.")
    if actual > ACTUAL_MAX_RATIO * expected:
        return (f"{actual:.2f}mm moved but only {expected:.0f}mm was requested "
                f"(> {ACTUAL_MAX_RATIO * 100:.0f}%). Check your marks and measurements.")
    return None


def calc_esteps(old_esteps: float, expected: float, actual: float) -> float:
    """
    Compute the calibrated E-steps value (Marlin).

    Synopsis: new = old * (expected / actual). Raises ValueError when the
        actual extrusion is invalid (see validate_actual_extruded).
    Parameters: Current E-steps; expected and actual extruded mm.
    Returns: New E-steps rounded to 2 decimals.
    """
    reason = validate_actual_extruded(actual, expected)
    if reason is not None:
        raise ValueError(reason)
    return round(old_esteps * (expected / actual), 2)


def calc_rotation_distance(old_rotation_distance: float, expected: float, actual: float) -> float:
    """
    Compute the calibrated extruder rotation distance (Klipper).

    Synopsis: new = old * (actual / expected). Raises ValueError when the
        actual extrusion is invalid (see validate_actual_extruded).
    Parameters: Current rotation distance; expected and actual extruded mm.
    Returns: New rotation distance rounded to 4 decimals.
    """
    reason = validate_actual_extruded(actual, expected)
    if reason is not None:
        raise ValueError(reason)
    return round(old_rotation_distance * (actual / expected), 4)


def calc_flow_ratio_orca(old_flow: float, modifier: float) -> float:
    """
    Compute the new flow ratio from an OrcaSlicer flow-rate modifier.

    Synopsis: new = old * (100 + modifier) / 100.
    Parameters: Current flow ratio; modifier percentage from the test print.
    Returns: New flow ratio rounded to 4 decimals.
    """
    return round(old_flow * (100.0 + modifier) / 100.0, 4)


def calc_flow_ratio_wall(old_flow: float, expected: float, measured: float) -> float:
    """
    Compute the new flow ratio from wall thickness measurements.

    Synopsis: new = old * (expected thickness / measured thickness).
    Parameters: Current flow ratio; expected and measured wall thickness mm.
    Returns: New flow ratio rounded to 4 decimals.
    """
    return round(old_flow * (expected / measured), 4)


def z_rotation_distance_raw(old_rotation_distance: float, measured_z: float,
                            expected_z: float) -> float:
    """
    Raw Z rotation distance formula (no guard, unrounded).

    Synopsis: new = old * (measured / expected). Single source of truth
        for the Z math - the guarded calculator and the manual override
        both call this function.
    Parameters: Current rotation distance; measured and expected Z in mm.
    Returns: New (unrounded) rotation distance.
    """
    return old_rotation_distance * (measured_z / expected_z)


def calc_z_rotation_distance(old_rotation_distance: float, expected_z: float,
                             measured_z: float) -> float:
    """
    Compute the new Z rotation distance, rejecting implausible corrections.

    Synopsis: new = old * (measured / expected). Corrections above 2%
        raise ValueError - that magnitude points to a mechanical problem
        (lead screw, coupler, Z offset), not a calibration tweak.
    Parameters: Current rotation distance; expected and measured Z in mm.
    Returns: New rotation distance rounded to 4 decimals.
    """
    new_value = z_rotation_distance_raw(old_rotation_distance, measured_z, expected_z)
    if abs(new_value / old_rotation_distance - 1.0) > MAX_Z_CORRECTION + 1e-9:  # epsilon: exactly 2% is allowed
        raise ValueError(
            f"Correction is {abs(new_value / old_rotation_distance - 1.0) * 100:.2f}% "
            f"(> {MAX_Z_CORRECTION * 100:.0f}%). This is almost certainly a mechanical "
            f"problem - check the lead screw, coupler and first layer before trusting it."
        )
    return round(new_value, 4)


logo = r"""
    __    ____  _____________  __
   / /   / __ \/ ____/ ____/ |/ /
  / /   / /_/ / / __/ __/  |   /
 / /___/ _, _/ /_/ / /___ /   |  
/_____/_/ |_|\____/_____//_/|_|  
                                                            
""" + f"LRGEX {Fore.BLUE}3D{Style.RESET_ALL} Printers Calculator {Fore.YELLOW}v2.0.3{Style.RESET_ALL}"

def calibrate_esteps():
    """
    Calibrate E-steps for Marlin firmware extruders.
    
    This function helps calculate the correct E-steps value by measuring
    the actual vs expected extrusion amount.
    """
    print(f"\n{Fore.YELLOW}=== E-steps Calibration (Marlin) ==={Style.RESET_ALL}")
    print(f"{Fore.CYAN}📋 Process: 5 steps | Duration: ~5 minutes{Style.RESET_ALL}")
    print("\n💡 This calibration ensures your extruder pushes the exact amount of filament requested.")
    print("   You'll need to manually measure filament to get accurate results.\n")
    
    print(f"{Fore.BLUE}Step 1/5:{Style.RESET_ALL} Get current E-steps value")
    print("   📍 In Marlin: Configuration → Advanced Settings → Steps/mm → E-steps")
    old_esteps = get_float_input("   Enter current E-steps value: ", min_value=MIN_ESTEPS, max_value=MAX_ESTEPS)
    
    print(f"\n{Fore.BLUE}Step 2/5:{Style.RESET_ALL} Set extrusion amount")
    expected_extrusion = get_float_input("   Enter expected extrusion (default: 100mm): ",
                                        min_value=MIN_EXTRUSION_LENGTH, max_value=MAX_EXTRUSION_LENGTH,
                                        default=DEFAULT_EXTRUSION_LENGTH)

    print(f"\n{Fore.BLUE}Step 3/5:{Style.RESET_ALL} Prepare for measurement")
    measurement_length = get_float_input(f"   Enter the marked length (mm): ",
                                        min_value=expected_extrusion + 1, max_value=MAX_MARKED_LENGTH,
                                        default=MEASUREMENT_LENGTH)
    print(f"   📏 Mark {measurement_length:.0f}mm from filament inlet")
    print("   ✏️  Mark it with a pen or tape")
    print("   🔥 Heat your hotend to printing temperature")
    input("   Press Enter when ready...")
    
    print(f"\n{Fore.BLUE}Step 4/5:{Style.RESET_ALL} Extrude filament")
    print(f"   🎯 Extrude exactly {expected_extrusion:.0f}mm from your printer")
    print(f"   📱 Use: Menu → Move Axis → Extruder → {expected_extrusion:.0f}mm")
    while True:
        leftover = get_float_input("   Enter leftover filament length (e.g., 22.58 mm): ",
                                  min_value=0, max_value=measurement_length, allow_zero=True)
        actual_extruded = measurement_length - leftover
        reason = validate_actual_extruded(actual_extruded, expected_extrusion)
        if reason is None:
            break
        print(f"   {Fore.RED}❌ {reason}{Style.RESET_ALL}")
        print("   Check your marks and measurements, then re-enter the leftover.\n")
    new_esteps = calc_esteps(old_esteps, expected_extrusion, actual_extruded)
    
    print(f"\n{Fore.BLUE}Step 5/5:{Style.RESET_ALL} Results & Next Steps")
    print(f"\n{Fore.GREEN}=== Calibration Results ==={Style.RESET_ALL}")
    print(f"   Expected extrusion: {expected_extrusion:.1f}mm")
    print(f"   Actual extrusion: {actual_extruded:.2f}mm")
    print(f"   Accuracy: {(actual_extruded/expected_extrusion*100):.1f}%")
    print(f"\n   🎯 Your new calibrated E-steps: {Fore.YELLOW}{new_esteps:.2f}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}📝 How to apply this setting:{Style.RESET_ALL}")
    print("   1. Go to: Configuration → Advanced Settings → Steps/mm")
    print(f"   2. Set E-steps to: {new_esteps:.2f}")
    print("   3. Save settings (Store to EEPROM)")
    print("   4. Test with a small print to verify")
    
    if abs(actual_extruded - expected_extrusion) > 7:
        print(f"\n{Fore.YELLOW}⚠️  Large deviation detected. Consider re-running calibration.{Style.RESET_ALL}")
    input(CONTINUE_PROMPT)
    
def calibrate_rotation_distance():
    """
    Calibrate rotation_distance for Klipper firmware extruders.
    
    This function calculates the correct rotation_distance value by measuring
    actual vs expected extrusion length.
    """
    print(f"\n{Fore.YELLOW}=== Rotation Distance Calibration (Klipper) ==={Style.RESET_ALL}")
    print(f"{Fore.CYAN}📋 Process: 4 steps | Duration: ~5 minutes{Style.RESET_ALL}")
    print("\n💡 This calibration ensures your Klipper extruder moves the exact filament amount.")
    print("   Similar to E-steps but uses rotation_distance parameter.\n")
    
    print(f"{Fore.BLUE}Step 1/4:{Style.RESET_ALL} Get current rotation_distance")
    print(f"\n{Fore.CYAN}📍 Look in your printer.cfg file for:{Style.RESET_ALL}")
    print(f"   {Fore.WHITE}[extruder]{Style.RESET_ALL}")
    print(f"   {Fore.YELLOW}rotation_distance: X.XXX{Style.RESET_ALL}")
    print("   (Usually between 1-50, common values: 7.71, 22.67, 33.5)")
    old_rotation_distance = get_float_input("\n   Enter current rotation_distance value: ", 
                                           min_value=MIN_ROTATION_DISTANCE, max_value=MAX_EXTRUDER_ROTATION_DISTANCE)
    
    print(f"\n{Fore.BLUE}Step 2/4:{Style.RESET_ALL} Set extrusion amount")
    expected_extrusion = get_float_input("   Enter expected extrusion (default: 100mm): ",
                                        min_value=MIN_EXTRUSION_LENGTH, max_value=MAX_EXTRUSION_LENGTH,
                                        default=DEFAULT_EXTRUSION_LENGTH)

    print(f"\n{Fore.BLUE}Step 3/4:{Style.RESET_ALL} Measure and extrude")
    measurement_length = get_float_input(f"   Enter the marked length (mm): ",
                                        min_value=expected_extrusion + 1, max_value=MAX_MARKED_LENGTH,
                                        default=MEASUREMENT_LENGTH)
    print(f"   📏 Mark {measurement_length:.0f}mm from filament inlet")
    print("   ✏️  Mark it with a pen or tape")
    print("   🔥 Heat your hotend to printing temperature")
    print(f"   🎯 Extrude exactly {expected_extrusion:.0f}mm using Klipper command:")
    print(f"   📱 EXTRUDE LENGTH={expected_extrusion:.0f} VELOCITY=5")
    while True:
        leftover = get_float_input("   Enter leftover filament length (e.g., 22.58 mm): ",
                                  min_value=0, max_value=measurement_length, allow_zero=True)
        actual_extruded = measurement_length - leftover
        reason = validate_actual_extruded(actual_extruded, expected_extrusion)
        if reason is None:
            break
        print(f"   {Fore.RED}❌ {reason}{Style.RESET_ALL}")
        print("   Check your marks and measurements, then re-enter the leftover.\n")
    new_rot_distance = calc_rotation_distance(old_rotation_distance, expected_extrusion, actual_extruded)

    print(f"\n{Fore.BLUE}Step 4/4:{Style.RESET_ALL} Results & Next Steps")
    print(f"\n{Fore.GREEN}=== Calibration Results ==={Style.RESET_ALL}")
    print(f"   Expected extrusion: {expected_extrusion:.1f}mm")
    print(f"   Actual extrusion: {actual_extruded:.2f}mm")
    print(f"   Accuracy: {(actual_extruded/expected_extrusion*100):.1f}%")
    print(f"\n   🎯 Your new calibrated rotation_distance: {Fore.YELLOW}{new_rot_distance:.4f}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}📝 How to apply this setting:{Style.RESET_ALL}")
    print("   1. Edit your printer.cfg file")
    print("   2. In [extruder] section, update:")
    print(f"      {Fore.YELLOW}rotation_distance: {new_rot_distance:.4f}{Style.RESET_ALL}")
    print("   3. Save file and restart Klipper")
    print("   4. Test with a small print to verify")
    
    if abs(actual_extruded - expected_extrusion) > 7:
        print(f"\n{Fore.YELLOW}⚠️  Large deviation detected. Consider re-running calibration.{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}💡 Pro tip:{Style.RESET_ALL} You can also use 'SAVE_CONFIG' in Klipper console to save automatically.")
    input(CONTINUE_PROMPT)


def calibrate_flow_ratio():
    """
    Calibrate the slicer flow ratio (e.g. OrcaSlicer).
    
    Supports two methods:
    1. OrcaSlicer Flow Rate calibration results
    2. Manual wall thickness measurement
    """
    print(f"\n{Fore.YELLOW}=== Flow Ratio Calibration (Slicer) ==={Style.RESET_ALL}")
    print("\nChoose the flow calibration method:")
    print("1. By using OrcaSlicer Flow Measure")
    print("2. 3D Printed Wall Thickness Measure")
    
    method = get_menu_choice(['1', '2'])

    if method == "1":
        print("\nYou can get the Modifier value from the slicer's Flow Rate calibration print.")
        old_flow_ratio = get_float_input("- Enter current flow ratio (e.g., 0.92): ", 
                                        min_value=MIN_FLOW_RATIO, max_value=MAX_FLOW_RATIO)
        modifier = get_float_input("- Enter the flow rate modifier from calibration (e.g., +5 or -3): ", 
                                  min_value=MIN_FLOW_MODIFIER, max_value=MAX_FLOW_MODIFIER,
                                  allow_zero=True, allow_negative=True)

        new_flow_ratio = calc_flow_ratio_orca(old_flow_ratio, modifier)

    elif method == "2":
        print("\nUsing Wall Thickness Measurement Method")
        print(f"{Fore.YELLOW}⚠️  Calipers squeeze single walls - the OrcaSlicer method (1) is more reliable.{Style.RESET_ALL}")
        print("")
        time.sleep(1)
        print(f"It is advisable to print {Fore.YELLOW}LRGEX flow text v1{Style.RESET_ALL} to measure the wall thickness, or create a cube with 0.4 walls no infill and no top layers")
        old_flow_ratio = get_float_input("- Enter current flow ratio (e.g., 0.92): ", 
                                        min_value=MIN_FLOW_RATIO, max_value=MAX_FLOW_RATIO)
        expected_thickness = get_float_input("- Enter expected wall thickness (e.g., 0.4): ", 
                                           min_value=MIN_WALL_THICKNESS, max_value=MAX_WALL_THICKNESS)
        measured_thickness = get_float_input("- Enter measured wall thickness (e.g., 0.36): ", 
                                           min_value=MIN_WALL_THICKNESS, max_value=MAX_WALL_THICKNESS)

        new_flow_ratio = calc_flow_ratio_wall(old_flow_ratio, expected_thickness, measured_thickness)
    
    print(f"\n{Fore.GREEN}=== Calibration Results ==={Style.RESET_ALL}")
    print(f"Your new {Fore.GREEN}calibrated flow ratio:{Style.RESET_ALL} {Fore.YELLOW}{new_flow_ratio:.4f}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}📝 How to apply this setting:{Style.RESET_ALL}")
    print("   1. In your slicer: Filament settings -> Flow ratio")
    print(f"      Set it to: {Fore.YELLOW}{new_flow_ratio:.4f}{Style.RESET_ALL}")
    print("   2. Print a small test object to verify")
    input(CONTINUE_PROMPT)


def calibrate_z_rotation_distance():
    """
    Calibrate the Z rotation distance for Klipper lead-screw Z axes.

    X/Y belt-driven axes are intentionally NOT calibrated here: their
    rotation distance is mechanically fixed (belt pitch x pulley teeth),
    and print dimension errors on X/Y belong to slicer/flow compensation.
    """
    print(f"\n{Fore.YELLOW}=== Z Rotation Distance Calibration (Klipper, Lead Screw) ==={Style.RESET_ALL}")
    print(f"{Fore.CYAN}📋 Process: 3 steps | Requires a tall test print{Style.RESET_ALL}")

    print(f"\n{Fore.YELLOW}⚠️  Read this first:{Style.RESET_ALL}")
    print("   • X/Y belt-driven axes: use the MECHANICAL rotation distance")
    print("     (belt pitch x pulley teeth, e.g. GT2 belt + 20T pulley = 40).")
    print("     Do NOT calibrate X/Y rotation_distance from print dimensions.")
    print("   • X/Y dimension errors are a slicer/flow issue - use Flow Ratio or")
    print("     the Dimensional Accuracy calibration instead.\n")

    print(f"{Fore.BLUE}Step 1/3:{Style.RESET_ALL} Get current Z rotation_distance")
    print(f"\n{Fore.CYAN}📍 In printer.cfg, find the [stepper_z] section:{Style.RESET_ALL}")
    print(f"   {Fore.WHITE}[stepper_z]{Style.RESET_ALL}")
    print(f"   {Fore.YELLOW}rotation_distance: X.XXX{Style.RESET_ALL}")
    print("   (Usually the lead screw lead, e.g. 8 for TR8x8, 2 for TR8x2)")
    old_rotation_distance = get_float_input("\n   Enter current Z rotation_distance: ",
                                           min_value=MIN_ROTATION_DISTANCE, max_value=MAX_ROTATION_DISTANCE)

    print(f"\n{Fore.BLUE}Step 2/3:{Style.RESET_ALL} Test print height")
    print("   📏 Print (or reuse) a tall test object and measure its height")
    expected_z = get_float_input(f"   Enter expected Z height (min {MIN_Z_TEST_HEIGHT:.0f}mm): ",
                                min_value=MIN_Z_TEST_HEIGHT, max_value=MAX_Z_DIMENSION)
    print(f"   {Fore.YELLOW}⚠️  First layer squish / Z offset affects height accuracy.{Style.RESET_ALL}")
    print("      Measure with calipers at the middle of the print if possible.")

    print(f"\n{Fore.BLUE}Step 3/3:{Style.RESET_ALL} Measured height & result")
    while True:
        measured_z = get_float_input("   Enter measured Z height: ",
                                    min_value=MIN_Z_TEST_HEIGHT * 0.5, max_value=MAX_Z_DIMENSION)
        try:
            new_rot_distance = calc_z_rotation_distance(old_rotation_distance, expected_z, measured_z)
            break
        except ValueError as reason:
            print(f"   {Fore.RED}❌ {reason}{Style.RESET_ALL}")
            confirm = input("   Use this value anyway? (y/n): ").strip().lower()
            if confirm in ("y", "yes"):
                new_rot_distance = round(z_rotation_distance_raw(old_rotation_distance, measured_z, expected_z), 4)
                print(f"   {Fore.YELLOW}⚠️  Overriding the 2% guard - double-check your mechanics.{Style.RESET_ALL}")
                break
            print("   Re-measure and re-enter the height.\n")

    print(f"\n{Fore.GREEN}=== Calibration Results ==={Style.RESET_ALL}")
    print(f"   Expected height: {expected_z:.1f}mm")
    print(f"   Measured height: {measured_z:.2f}mm")
    print(f"\n   🎯 Your new calibrated Z rotation_distance: {Fore.YELLOW}{new_rot_distance:.4f}{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}📝 How to apply this setting:{Style.RESET_ALL}")
    print("   1. Edit your printer.cfg file, [stepper_z] section:")
    print(f"      {Fore.YELLOW}rotation_distance: {new_rot_distance:.4f}{Style.RESET_ALL}")
    print("   2. Save file and restart Klipper (or use SAVE_CONFIG)")
    input(CONTINUE_PROMPT)

# ============================================================
# Dimensional Accuracy Calibration (OrcaSlicer)
# Two-square + holes method: fits a per-axis linear error model
# (slope = fractional scale error, offset = fixed width error) and
# converts it into OrcaSlicer shrinkage / contour / hole compensation.
# ============================================================


# ---------- Pure math (unit-tested in tests/test_dimcal.py) ----------

def dimcal_axis_fit(small_nom: float, large_nom: float,
                    meas_small: float, meas_large: float) -> tuple[float, float]:
    """
    Fit the linear error model for one axis.

    Synopsis: Derives the fractional scale error (slope) and the fixed width
        error (offset, total of both sides) from the small/large square pair.
    Parameters: Nominal and measured sizes in mm for one axis.
    Returns: (slope, offset)
    """
    e_s = meas_small - small_nom
    e_l = meas_large - large_nom
    slope = (e_l - e_s) / (large_nom - small_nom)
    offset = e_s - slope * small_nom
    return slope, offset


def dimcal_orca_values(slope_avg: float, offset_avg: float) -> tuple[float, float]:
    """
    Convert averaged axis model into OrcaSlicer values.

    Synopsis: Shrinkage XY % = 100*(1+slope); X-Y contour compensation =
        -offset/2 (Orca applies compensation per side).
    Parameters: Averaged slope and offset over X and Y.
    Returns: (shrinkage_percent, contour_compensation)
    """
    shrinkage = round(100.0 * (1.0 + slope_avg), 2)
    contour = round(-offset_avg / 2.0, 3)
    return shrinkage, contour


def dimcal_hole_comp(hole_nom: float, hole_meas: float, slope_avg: float) -> float:
    """
    Per-side hole compensation for one measured hole.

    Synopsis: Removes the scale error from the hole first, then halves the
        residual into a per-side compensation value.
    Parameters: Nominal and measured hole diameters in mm; averaged slope.
    Returns: Per-side hole compensation in mm.
    """
    residual = hole_meas - hole_nom * (1.0 + slope_avg)
    return -residual / 2.0


# ---------- Pure validators (unit-tested) ----------

def validate_square_sizes(small: float, large: float) -> str | None:
    """
    Validate the small/large square size pair.

    Synopsis: Enforces large > small and large >= 3x small so the slope
        math stays reliable.
    Parameters: Square side lengths in mm.
    Returns: None if valid, otherwise the rejection reason.
    """
    if large <= small:
        return "Large square must be bigger than the small square."
    if large < SIZE_RATIO_MIN * small:
        return (f"Large square must be at least {SIZE_RATIO_MIN:.0f}x the small square "
                f"(otherwise the slope math is unreliable).")
    return None


def validate_bed_fit(small: float, large: float,
                     bed_x: float = BED_MAX_X, bed_y: float = BED_MAX_Y,
                     gap: float = BED_GAP_MIN) -> str | None:
    """
    Check both squares fit the bed together with the minimum gap.

    Synopsis: Squares are placed side by side; the span (small + gap + large)
        must fit one bed axis, and each square must fit both axes.
    Parameters: Square side lengths, bed size and minimum gap in mm.
    Returns: None if valid, otherwise the rejection reason.
    """
    if large > bed_x or large > bed_y:
        return f"Large square ({large:.0f}mm) does not fit the {bed_x:.0f}x{bed_y:.0f} bed."
    span = small + gap + large
    if span > bed_x and span > bed_y:
        return (f"Both squares plus the {gap:.0f}mm gap need {span:.0f}mm side by side, "
                f"but the bed is only {bed_x:.0f}x{bed_y:.0f}mm.")
    return None


def layout_holes_row(side: float, diameters: list[float],
                     margin: float = HOLE_MARGIN) -> list[float] | None:
    """
    Auto-layout holes in one centered horizontal row.

    Synopsis: Places the holes left to right with `margin` between them and
        at least `margin` to each square edge; the row is centered.
    Parameters: Square side in mm; hole diameters in mm; spacing margin in mm.
    Returns: Hole center X positions (from the left edge), or None if they
        do not fit.
    """
    if not diameters:
        return []
    used = sum(diameters) + margin * (len(diameters) - 1)
    if used + 2.0 * margin > side:
        return None
    positions: list[float] = []
    cursor = (side - used) / 2.0
    for d in diameters:
        cursor += d / 2.0
        positions.append(cursor)
        cursor += d / 2.0 + margin
    return positions


def validate_holes(side: float, diameters: list[float]) -> str | None:
    """
    Validate hole diameters and row fit for one square.

    Synopsis: Enforces minimum diameter, minimum wall to the edges, and that
        all holes fit in a single row with the spacing margin.
    Parameters: Square side in mm; hole diameters in mm.
    Returns: None if valid, otherwise the rejection reason.
    """
    for d in diameters:
        if d < HOLE_MIN_DIAMETER:
            return f"Hole \u2300{d:g}mm is below the {HOLE_MIN_DIAMETER:.0f}mm minimum."
        if d > side - 2.0 * HOLE_MARGIN:
            return (f"Hole \u2300{d:g}mm leaves less than {HOLE_MARGIN:.0f}mm wall inside a "
                    f"{side:.0f}mm square (max \u2300{side - 2.0 * HOLE_MARGIN:g}mm).")
    if diameters and layout_holes_row(side, diameters) is None:
        wanted = ", ".join(f"\u2300{d:g}" for d in diameters)
        return (f"Holes {wanted}mm do not fit in a row inside {side:.0f}mm with "
                f"{HOLE_MARGIN:.0f}mm spacing - use fewer or smaller holes.")
    return None


# ---------- Persistence ----------

def _save_json(path: Path, data) -> None:
    """Write JSON data to disk (UTF-8, context manager)."""
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.success(f"Saved {path.name}")
    except OSError as e:
        logger.error(f"Failed to write {path.name}: {e}")


def _load_json(path: Path):
    """Read JSON data from disk; returns None and logs on failure."""
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Failed to read {path.name}: {e}")
        return None


def _load_setups() -> dict:
    """
    Load all saved dimensional accuracy setups.

    Synopsis: The setup file is a dict keyed by filament name so every
        filament keeps its own setup instead of one overwritten file.
        A v2.0.1 legacy flat file is migrated under its filament key;
        malformed entries are dropped instead of crashing.
    Returns: Dict of filament -> setup (empty when no file exists).
    """
    data = _load_json(DIMCAL_SETUP_FILE)
    if not isinstance(data, dict):
        return {}
    if isinstance(data.get("filament"), str):
        return {data["filament"]: data}  # v2.0.1 legacy flat file
    return {k: v for k, v in data.items() if isinstance(v, dict)}


def _pick_setup() -> dict | None:
    """
    Pick which filament setup to use.

    Synopsis: With exactly one setup it is used directly; with several
        the user chooses from a numbered list.
    Returns: The chosen setup dict, or None when nothing is saved.
    """
    setups = _load_setups()
    if not setups:
        print(f"{Fore.RED}\u274c No saved setup found. Run 'New setup' first.{Style.RESET_ALL}")
        return None
    names = list(setups.keys())
    if len(names) == 1:
        return setups[names[0]]
    print("\n   Saved filament setups:")
    for i, name in enumerate(names, 1):
        print(f"      {i}. {name}")
    idx = _ask_int(f"   Select setup number [1-{len(names)}]: ",
                   default=1, min_value=1, max_value=len(names))
    return setups[names[idx - 1]]


# ---------- Interactive steps ----------

def _ask_int(prompt: str, default: int, min_value: int, max_value: int) -> int:
    """Ask for an integer with bounds and a default."""
    while True:
        raw = input(prompt).strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            print(f"\u274c Please enter a whole number.")
            continue
        if min_value <= value <= max_value:
            return value
        print(f"\u274c Value must be between {min_value} and {max_value}.")


def _ask_holes(square_label: str, side: float, defaults: list[float]) -> list[float]:
    """Ask hole count and diameters for one square, validating layout."""
    while True:
        count = _ask_int(f"   How many holes in the {square_label} [{len(defaults)}]: ",
                         default=len(defaults), min_value=0, max_value=12)
        diameters: list[float] = []
        for i in range(count):
            default = defaults[i] if i < len(defaults) else None
            default_txt = f" [{default:g}]" if default is not None else ""
            d = get_float_input(f"   Hole {i + 1} diameter in mm{default_txt}: ",
                                min_value=0.5, max_value=side, default=default)
            diameters.append(d)
        reason = validate_holes(side, diameters)
        if reason is None:
            return diameters
        print(f"\n   {Fore.RED}\u274c {reason}{Style.RESET_ALL}")
        print("   Let's try the holes again.\n")


def dimcal_setup() -> None:
    """
    Interactive setup wizard for the dimensional accuracy test.

    Synopsis: Asks filament type, square sizes, height and holes with full
        validation, then prints a build sheet + print instructions and saves
        the setup for the measurement step.
    Parameters: None (interactive).
    Returns: None
    """
    print(f"\n{Fore.YELLOW}=== \U0001f4cf Dimensional Accuracy - New Setup ==={Style.RESET_ALL}")
    print(f"{Fore.CYAN}\U0001f4cb Process: setup wizard | for OrcaSlicer dimensional calibration{Style.RESET_ALL}")
    print("\n\U0001f4a1 Prints TWO squares with holes; the size difference separates\n"
          "   scale error (shrinkage) from fixed width error (compensation).\n")

    raw = input(f"Filament type/brand [{DEFAULT_FILAMENT}]: ").strip()
    filament = raw if raw else DEFAULT_FILAMENT

    while True:
        small = get_float_input(f"Small square size in mm [{DEFAULT_SMALL_SQUARE:g}]: ",
                                min_value=10, max_value=200, default=DEFAULT_SMALL_SQUARE)
        large = get_float_input(f"Large square size in mm [{DEFAULT_LARGE_SQUARE:g}]: ",
                                min_value=20, max_value=250, default=DEFAULT_LARGE_SQUARE)
        reason = validate_square_sizes(small, large) or validate_bed_fit(small, large)
        if reason is None:
            break
        print(f"\n{Fore.RED}\u274c {reason}{Style.RESET_ALL}\n")

    height = get_float_input(f"Height in mm [{DEFAULT_HEIGHT:g}]: ",
                             min_value=1, max_value=100, default=DEFAULT_HEIGHT)

    print(f"\n{Fore.CYAN}\u2300 Holes in the small square ({small:.0f}mm):{Style.RESET_ALL}")
    small_holes = _ask_holes(f"small square ({small:.0f}mm)", small, DEFAULT_SMALL_HOLES)
    print(f"\n{Fore.CYAN}\u2300 Holes in the large square ({large:.0f}mm):{Style.RESET_ALL}")
    large_holes = _ask_holes(f"large square ({large:.0f}mm)", large, DEFAULT_LARGE_HOLES)

    print(f"\n{Fore.GREEN}=== Setup Summary ==={Style.RESET_ALL}")
    print(f"   Filament:      {Fore.YELLOW}{filament}{Style.RESET_ALL}")
    print(f"   Small square:  {small:g} x {small:g} x {height:g} mm")
    print(f"   Large square:  {large:g} x {large:g} x {height:g} mm")
    _print_holes("Small", small, small_holes)
    _print_holes("Large", large, large_holes)

    confirm = input("\nProceed with this setup? (y/n): ").strip().lower()
    if confirm not in ["y", "yes"]:
        print("Setup cancelled.")
        return

    setups = _load_setups()
    setups[filament] = {
        "filament": filament,
        "small": small,
        "large": large,
        "height": height,
        "small_holes": small_holes,
        "large_holes": large_holes,
        "created": datetime.now().isoformat(timespec="seconds"),
    }
    _save_json(DIMCAL_SETUP_FILE, setups)

    _print_build_sheet(filament, small, large, height, small_holes, large_holes)
    input(CONTINUE_PROMPT)


def _print_holes(label: str, side: float, holes: list[float]) -> None:
    """Print one square's hole row summary with positions."""
    if not holes:
        print(f"   {label} holes:   none")
        return
    positions = layout_holes_row(side, holes) or []
    pos_txt = ", ".join(f"{p:.1f}" for p in positions)
    print(f"   {label} holes:   " + ", ".join(f"\u2300{d:g}" for d in holes)
          + f" mm (centers at {pos_txt} mm)")


def _print_build_sheet(filament: str, small: float, large: float, height: float,
                       small_holes: list[float], large_holes: list[float]) -> None:
    """Print the CAD build sheet and the OrcaSlicer print instructions."""
    print(f"\n{Fore.BLUE}\U0001f4dd BUILD SHEET - create these two models in your CAD:{Style.RESET_ALL}")
    _print_square_spec("Square 1 (small)", small, height, small_holes)
    _print_square_spec("Square 2 (large)", large, height, large_holes)
    print(f"\n   {Fore.YELLOW}\u26a0\ufe0f  Export circles at high quality (>= 128 segments / \"High\" refinement){Style.RESET_ALL}")
    print("      so faceting cannot pollute the hole measurements.\n")

    print(f"{Fore.BLUE}\U0001f5a5\ufe0f  Print settings in OrcaSlicer (critical):{Style.RESET_ALL}")
    print("   - Filament settings -> Shrinkage (XY): 100 %")
    print("   - Process -> Quality -> Precision -> X-Y contour compensation: 0")
    print("   - Process -> Quality -> Precision -> X-Y hole compensation: 0")
    print("   - Polyholes: OFF")
    print("   - Infill: 15 %")
    print(f"\n{Fore.BLUE}\U0001f4cf After printing:{Style.RESET_ALL}")
    print("   - Cool the parts 30 minutes before measuring")
    print("   - Measure at MID-HEIGHT of the part")
    print("   - Take 2-3 readings per dimension and use the average")
    print(f"\n{Fore.CYAN}When done, come back and run 'Enter measurements'.{Style.RESET_ALL}")


def _print_square_spec(label: str, side: float, height: float, holes: list[float]) -> None:
    """Print one square's CAD specification line block."""
    if holes:
        positions = layout_holes_row(side, holes) or []
        pos_txt = ", ".join(f"{p:.1f}" for p in positions)
        print(f"   {label}: {side:g} x {side:g} x {height:g} mm with "
              f"{len(holes)} hole(s) \u2300" + "/".join(f"{d:g}" for d in holes)
              + f" mm (centers at {pos_txt} mm, mid-height)")
    else:
        print(f"   {label}: {side:g} x {side:g} x {height:g} mm, no holes")


def measurement_bounds(nominal: float, hole: bool = False) -> tuple[float, float]:
    """
    Compute the accepted measurement bounds for a nominal size.

    Synopsis: Squares use +/-3% (MEAS_TOLERANCE). Holes use absolute
        bounds nominal +/- max(HOLE_MEAS_TOLERANCE_MM, 10% of nominal),
        because small holes legitimately deviate far more than 3%.
    Parameters: Nominal size in mm; True for holes.
    Returns: (lower, upper) accepted bounds in mm.
    """
    if hole:
        tol = max(HOLE_MEAS_TOLERANCE_MM, 0.10 * nominal)
        return nominal - tol, nominal + tol
    return nominal * (1.0 - MEAS_TOLERANCE), nominal * (1.0 + MEAS_TOLERANCE)


def _ask_measured(prompt: str, nominal: float, hole: bool = False) -> float:
    """Ask for a measurement within the accepted bounds (re-asks with reason)."""
    lo, hi = measurement_bounds(nominal, hole)
    return get_float_input(prompt, min_value=lo, max_value=hi)


def dimcal_measure() -> None:
    """
    Measurement entry + calibration calculation.

    Synopsis: Loads the saved setup, asks every measurement by name with
        bounds (squares +/-3%, holes +/- max(0.5mm, 10%)), runs the
        slope/offset model and prints the OrcaSlicer
        values with warnings; appends results to history.
    Parameters: None (interactive).
    Returns: None
    """
    setup = _pick_setup()
    if setup is None:
        return
    s = setup["small"]
    l = setup["large"]
    small_holes = list(setup["small_holes"])
    large_holes = list(setup["large_holes"])

    print(f"\n{Fore.YELLOW}=== \U0001f4ca Dimensional Accuracy - Measurements ==={Style.RESET_ALL}")
    print(f"\n{Fore.CYAN}\U0001f4cb Filament: {setup['filament']} | squares {s:g}/{l:g} mm{Style.RESET_ALL}")
    print("\n\U0001f4cf Measure at mid-height, 2-3 readings each, enter the average.\n")

    print(f"{Fore.BLUE}Small square ({s:g} mm):{Style.RESET_ALL}")
    ms_x = _ask_measured(f"   X measured: ", s)
    ms_y = _ask_measured(f"   Y measured: ", s)
    ms_holes = [_ask_measured(f"   Hole \u2300{d:g} measured: ", d, hole=True) for d in small_holes]

    print(f"\n{Fore.BLUE}Large square ({l:g} mm):{Style.RESET_ALL}")
    ml_x = _ask_measured(f"   X measured: ", l)
    ml_y = _ask_measured(f"   Y measured: ", l)
    ml_holes = [_ask_measured(f"   Hole \u2300{d:g} measured: ", d, hole=True) for d in large_holes]

    # --- axis fits
    slope_x, offset_x = dimcal_axis_fit(s, l, ms_x, ml_x)
    slope_y, offset_y = dimcal_axis_fit(s, l, ms_y, ml_y)
    slope_avg = (slope_x + slope_y) / 2.0
    offset_avg = (offset_x + offset_y) / 2.0
    shrinkage, contour = dimcal_orca_values(slope_avg, offset_avg)

    # --- holes
    all_holes = [(d, m) for d, m in zip(small_holes, ms_holes)] + \
                [(d, m) for d, m in zip(large_holes, ml_holes)]
    hole_comps = [dimcal_hole_comp(d, m, slope_avg) for d, m in all_holes]
    hole_recommended = round(sum(hole_comps) / len(hole_comps), 3) if hole_comps else 0.0

    _print_results(setup, (ms_x, ms_y), (ml_x, ml_y),
                   (slope_x, offset_x, slope_y, offset_y),
                   shrinkage, contour, all_holes, hole_comps, hole_recommended,
                   ms_holes, ml_holes)
    _save_history(setup, shrinkage, contour, hole_recommended,
                  ms_x, ms_y, ml_x, ml_y, ms_holes, ml_holes)
    input(CONTINUE_PROMPT)


def _print_results(setup: dict, ms: tuple[float, float], ml: tuple[float, float], axes: tuple,
                   shrinkage: float, contour: float,
                   all_holes: list, hole_comps: list, hole_recommended: float,
                   ms_holes: list, ml_holes: list) -> None:
    """Print the results table, warnings and OrcaSlicer values."""
    slope_x, offset_x, slope_y, offset_y = axes
    s, l = setup["small"], setup["large"]

    print(f"\n{Fore.GREEN}=== Dimensional Accuracy Results ({setup['filament']}) ==={Style.RESET_ALL}")
    print(f"{'':4}{'Axis':6}{'err small':>10}{'err large':>10}{'slope':>10}{'offset':>9}")
    print(f"{'':4}{'X':6}{ms[0]-s:>+10.2f}{ml[0]-l:>+10.2f}{slope_x*100:>+10.4f}{offset_x:>+9.3f}")
    print(f"{'':4}{'Y':6}{ms[1]-s:>+10.2f}{ml[1]-l:>+10.2f}{slope_y*100:>+10.4f}{offset_y:>+9.3f}")
    slope_avg = (slope_x + slope_y) / 2.0
    offset_avg = (offset_x + offset_y) / 2.0
    print(f"\n    Combined: slope_avg = {slope_avg*100:+.4f}% | offset_avg = {offset_avg:+.3f} mm")

    print(f"\n{Fore.YELLOW}\u26a0\ufe0f  Warnings:{Style.RESET_ALL}")
    warned = False
    if abs(slope_x - slope_y) > AXIS_MISMATCH_WARN:
        print(f"   - X/Y slopes differ by {abs(slope_x - slope_y)*100:.2f}% (> 0.1%)")
        print(f"     {Fore.YELLOW}Likely belt tension / mechanical issue - fix that BEFORE trusting slicer values.{Style.RESET_ALL}")
        warned = True
    if abs(slope_avg) > SLOPE_ABNORMAL_WARN:
        print(f"   - Average slope is {abs(slope_avg)*100:.2f}% (> 0.8%) - abnormal.")
        print(f"     {Fore.YELLOW}Check belts/steps before trusting these slicer values.{Style.RESET_ALL}")
        warned = True
    if hole_comps and (max(hole_comps) - min(hole_comps)) > HOLE_SPREAD_WARN:
        print(f"   - Hole compensations spread over {max(hole_comps)-min(hole_comps):.3f}mm (> 0.05)")
        print(f"     {Fore.YELLOW}Small holes behave differently - use the value for the hole range you design most, or enable polyholes.{Style.RESET_ALL}")
        warned = True
    dup = _find_dup_holes(setup, ms_holes, ml_holes)
    for d, diff in dup:
        print(f"   - \u2300{d:g}mm exists in both squares but measures differ by {diff:.2f}mm (> 0.1mm)")
        warned = True
    if not warned:
        print("   none \u2705")

    print(f"\n{Fore.CYAN}\U0001f527 Holes (after scale correction):{Style.RESET_ALL}")
    print(f"{'':4}{'nominal':>9}{'measured':>10}{'comp':>8}")
    for (d, m), c in zip(all_holes, hole_comps):
        print(f"{'':4}{d:>9g}{m:>10.2f}{c:>+8.3f}")

    print(f"\n{Fore.GREEN}\U0001f3af OrcaSlicer values - enter these:{Style.RESET_ALL}")
    print(f"   Filament settings -> Shrinkage (XY):            {Fore.YELLOW}{shrinkage:g} %{Style.RESET_ALL}")
    print(f"   Process -> Quality -> Precision -> X-Y contour:  {Fore.YELLOW}{contour:+.3f}{Style.RESET_ALL}")
    print(f"   Process -> Quality -> Precision -> X-Y hole:     {Fore.YELLOW}{hole_recommended:+.3f}{Style.RESET_ALL}"
          + (f"  (mean of {len(hole_comps)} holes)" if hole_comps else ""))


def _find_dup_holes(setup: dict, ms_holes: list[float], ml_holes: list[float]) -> list[tuple[float, float]]:
    """Find same-diameter holes measured in both squares with a large difference."""
    small_map = {round(d, 3): m for d, m in zip(setup["small_holes"], ms_holes)}
    results: list[tuple[float, float]] = []
    for d, m in zip(setup["large_holes"], ml_holes):
        key = round(d, 3)
        if key in small_map and abs(small_map[key] - m) > HOLE_DUP_DIFF_WARN:
            results.append((d, abs(small_map[key] - m)))
    return results


def _save_history(setup: dict, shrinkage: float, contour: float,
                  hole_recommended: float,
                  ms_x: float, ms_y: float, ml_x: float, ml_y: float,
                  ms_holes: list, ml_holes: list) -> None:
    """Append this calibration to the history file (never overwritten)."""
    history = _load_json(DIMCAL_HISTORY_FILE)
    if not isinstance(history, list):
        history = []
    history.append({
        "filament": setup["filament"],
        "date": datetime.now().isoformat(timespec="seconds"),
        "setup": {k: setup[k] for k in ("small", "large", "height", "small_holes", "large_holes")},
        "measurements": {
            "small": {"x": ms_x, "y": ms_y},
            "large": {"x": ml_x, "y": ml_y},
            "small_holes": ms_holes,
            "large_holes": ml_holes,
        },
        "results": {
            "shrinkage_xy": shrinkage,
            "contour_comp": contour,
            "hole_comp": hole_recommended,
        },
    })
    _save_json(DIMCAL_HISTORY_FILE, history)


def dimcal_verify() -> None:
    """
    Verify mode: check a reprint made with the new Orca values.

    Synopsis: Loads the saved setup and the latest history entry, asks for
        the reprint measurements and reports per-item residuals; PASS when
        everything is within +/-0.1 mm of nominal.
    Parameters: None (interactive).
    Returns: None
    """
    setup = _pick_setup()
    if setup is None:
        return
    history = _load_json(DIMCAL_HISTORY_FILE)
    if not isinstance(history, list) or not history:
        print(f"{Fore.RED}\u274c No calibration history yet. Run 'Enter measurements' first.{Style.RESET_ALL}")
        return
    last = next((e for e in reversed(history) if e.get("filament") == setup["filament"]), None)
    if last is None:
        print(f"{Fore.RED}\u274c No history entry for '{setup['filament']}'. Measure first.{Style.RESET_ALL}")
        return

    print(f"\n{Fore.YELLOW}=== \u2705 Verify - {setup['filament']} ==={Style.RESET_ALL}")
    print(f"\n{Fore.CYAN}\U0001f4cb Reprint the squares with the calibrated values, then measure.{Style.RESET_ALL}")
    print(f"   Applied: shrinkage {last['results']['shrinkage_xy']:g}% | "
          f"contour {last['results']['contour_comp']:+.3f} | hole {last['results']['hole_comp']:+.3f}\n")

    s, l = setup["small"], setup["large"]
    items: list[tuple[str, float]] = []
    for label, nom in [(f"Small X ({s:g}mm)", s), (f"Small Y ({s:g}mm)", s)]:
        items.append((label, get_float_input(f"   {label} measured: ",
                                             min_value=nom * 0.5, max_value=nom * 1.5)))
    for d in setup["small_holes"]:
        items.append((f"Small hole \u2300{d:g}mm", get_float_input(
            f"   Small hole \u2300{d:g} measured: ", min_value=max(0.1, d * 0.5), max_value=d * 1.5)))
    for label, nom in [(f"Large X ({l:g}mm)", l), (f"Large Y ({l:g}mm)", l)]:
        items.append((label, get_float_input(f"   {label} measured: ",
                                             min_value=nom * 0.5, max_value=nom * 1.5)))
    for d in setup["large_holes"]:
        items.append((f"Large hole \u2300{d:g}mm", get_float_input(
            f"   Large hole \u2300{d:g} measured: ", min_value=max(0.1, d * 0.5), max_value=d * 1.5)))

    nominals: dict[str, float] = {}
    nominals[f"Small X ({s:g}mm)"] = s
    nominals[f"Small Y ({s:g}mm)"] = s
    for d in setup["small_holes"]:
        nominals[f"Small hole \u2300{d:g}mm"] = d
    nominals[f"Large X ({l:g}mm)"] = l
    nominals[f"Large Y ({l:g}mm)"] = l
    for d in setup["large_holes"]:
        nominals[f"Large hole \u2300{d:g}mm"] = d

    print(f"\n{Fore.GREEN}=== Verify Results ==={Style.RESET_ALL}")
    all_pass = True
    for label, measured in items:
        residual = measured - nominals[label]
        ok = abs(residual) <= VERIFY_TOLERANCE
        if not ok:
            all_pass = False
        status = "\u2705" if ok else "\u274c"
        print(f"   {label:<28}{residual:>+7.2f} mm  {status}")

    if all_pass:
        print(f"\n{Fore.GREEN}\U0001f3af PASS - everything within +/-{VERIFY_TOLERANCE:g} mm. Printer is dialed in!{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.YELLOW}\u26a0\ufe0f  FAIL - some dimensions exceed +/-{VERIFY_TOLERANCE:g} mm. "
              f"Re-run 'Enter measurements' with these new values.{Style.RESET_ALL}")
    input(CONTINUE_PROMPT)


def dimensional_accuracy_menu() -> None:
    """Submenu for the Dimensional Accuracy calibration module."""
    while True:
        print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
        print(f"    {Fore.YELLOW}\U0001f4cf Dimensional Accuracy Calibration (OrcaSlicer){Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
        print("\n   1. \U0001f195 New setup - sizes, holes & build sheet")
        print("   2. \U0001f4ca Enter measurements & calculate")
        print("   3. \u2705 Verify previous calibration")
        print("   4. \U0001f519 Back to main menu")
        choice = get_menu_choice(["1", "2", "3", "4"])
        if choice == "1":
            dimcal_setup()
        elif choice == "2":
            dimcal_measure()
        elif choice == "3":
            dimcal_verify()
        else:
            break


def show_help():
    """Display helpful information about calibrations and the tool."""
    print(f"\n{Fore.CYAN}📚 Help & Information{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    
    print(f"\n{Fore.YELLOW}🔧 What does each calibration do?{Style.RESET_ALL}")
    print("\n   🔩 E-steps (Marlin):")
    print("      Calibrates how much filament your extruder pushes per step.")
    print("      Use this for Marlin firmware printers.")
    
    print("\n   ⚙️  Rotation Distance (Klipper):")
    print("      Similar to E-steps but for Klipper firmware.")
    print("      Calibrates extruder motor rotation to filament movement.")
    
    print("\n   💧 Flow Ratio (Slicer):")
    print("      Slicer filament setting that fine-tunes how much plastic")
    print("      is extruded during printing. Fixes over/under-extrusion.")
    
    print("\n   📐 Z Rotation Distance (Klipper, lead screw):")
    print("      Calibrates Z height accuracy from a tall test print.")
    print("      X/Y belt axes keep their mechanical value (belt pitch x")
    print("      pulley teeth); X/Y dimension errors are a slicer/flow issue.")
    
    print("\n   \U0001f4cf Dimensional Accuracy (OrcaSlicer):")
    print("      Two squares with holes; separates shrinkage from compensation")
    print("      and computes the exact OrcaSlicer shrinkage/contour/hole values.")
    
    print(f"\n{Fore.YELLOW}🎯 Which calibration should I do first?{Style.RESET_ALL}")
    print("   1. Start with E-steps/Rotation Distance")
    print("   2. Then do Flow Ratio calibration") 
    print("   3. Z rotation distance (lead screw) if needed")
    print("   4. Last, Dimensional Accuracy for print-perfect dimensions")
    
    print(f"\n{Fore.YELLOW}⚠️  Important notes:{Style.RESET_ALL}")
    print("   • Heat your hotend before extruder calibrations")
    print("   • Use the same filament type you normally print with")
    print("   • Make sure your printer is mechanically sound first")
    print("   • Backup your current settings before changing them")
    
    print(f"\n{Fore.YELLOW}🔗 Need more help?{Style.RESET_ALL}")
    print("   • Check your printer's documentation")
    print("   • Visit printer communities and forums")
    print("   • Consult calibration guides online")
    
    input(CONTINUE_PROMPT)

def main():
    """Main application loop with improved menu handling."""
    while True:
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"    {Fore.YELLOW}🔧 3D Printer Calibration Utility{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"\n{Fore.WHITE}Choose a calibration type:{Style.RESET_ALL}")
        print(f"   1. 🔩 Calibrate E-steps for Extruder {Fore.GREEN}(Marlin){Style.RESET_ALL}")
        print(f"   2. ⚙️  Calibrate Rotation Distance for Extruder {Fore.GREEN}(Klipper){Style.RESET_ALL}")
        print(f"   3. 💧 Calibrate Flow Ratio {Fore.GREEN}(Slicer){Style.RESET_ALL}")
        print(f"   4. 📐 Calibrate Z Rotation Distance (Lead Screw) {Fore.GREEN}(Klipper){Style.RESET_ALL}")
        print(f"   5. 📏 Dimensional Accuracy {Fore.GREEN}(OrcaSlicer){Style.RESET_ALL}")
        print("   6. ❓ Help & Information")
        print("   7. 🚪 Exit")

        choice = get_menu_choice(['1', '2', '3', '4', '5', '6', '7'])

        if choice == '1':
            calibrate_esteps()
        elif choice == '2':
            calibrate_rotation_distance()
        elif choice == '3':
            calibrate_flow_ratio()
        elif choice == '4':
            calibrate_z_rotation_distance()
        elif choice == '5':
            dimensional_accuracy_menu()
        elif choice == '6':
            show_help()
        elif choice == '7':
            print(f"\n{Fore.GREEN}✨ Thank you for using the 3D Printer Calibration Utility!{Style.RESET_ALL}")
            print("🎯 Happy printing!")
            break
        

if __name__ == "__main__":
    try:
        print(logo)
        time.sleep(2)
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Program interrupted by user. Goodbye!{Style.RESET_ALL}")
    except Exception as e:
        traceback.print_exc()
        print(f"\n{Fore.RED}An unexpected error occurred: {e}{Style.RESET_ALL}")
        print("Please report this issue with the full traceback above.")