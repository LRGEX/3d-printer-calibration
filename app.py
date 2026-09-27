"""
3D Printer Calibration Utility

This utility provides calibration tools for 3D printers using both Marlin and Klipper firmware.
It includes calibration for E-steps, rotation distances, flow ratios, and axis calibration.

Features:
- Input validation with clear error messages
- Support for both Marlin and Klipper firmware
- Multiple calibration methods for flow ratio
- Color-coded output for better user experience

Author: LRGEX
Version: 2.0
Date: 2025-05-25
License: MIT License

"""

import time
from colorama import Fore, Style, init

# Initialize colorama (Fixes Windows CMD issues)
init(autoreset=True)

# Constants
CONTINUE_PROMPT = "\nPress Enter to continue..."
DEFAULT_CUBE_SIZE = 20.0
DEFAULT_EXTRUSION_LENGTH = 100.0
MEASUREMENT_LENGTH = 120.0
MIN_ESTEPS = 1.0
MAX_ESTEPS = 10000.0
MIN_ROTATION_DISTANCE = 0.1
MAX_ROTATION_DISTANCE = 100.0
MIN_FLOW_RATIO = 0.1
MAX_FLOW_RATIO = 2.0



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

logo = r"""
    __    ____  _____________  __
   / /   / __ \/ ____/ ____/ |/ /
  / /   / /_/ / / __/ __/  |   /
 / /___/ _, _/ /_/ / /___ /   |  
/_____/_/ |_|\____/_____//_/|_|  
                                                            
""" + f"LRGEX {Fore.BLUE}3D{Style.RESET_ALL} Printers Calculator {Fore.YELLOW}v2.0{Style.RESET_ALL}"

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
                                        min_value=10, max_value=200, default=DEFAULT_EXTRUSION_LENGTH)

    print(f"\n{Fore.BLUE}Step 3/5:{Style.RESET_ALL} Prepare for measurement")
    measurement_length = get_float_input(f"   Enter the marked length (mm): ",
                                        min_value=expected_extrusion + 1, max_value=1000)
    print(f"   📏 Mark {measurement_length:.0f}mm from filament inlet")
    print("   ✏️  Mark it with a pen or tape")
    print("   🔥 Heat your hotend to printing temperature")
    input("   Press Enter when ready...")
    
    print(f"\n{Fore.BLUE}Step 4/5:{Style.RESET_ALL} Extrude filament")
    print(f"   🎯 Extrude exactly {expected_extrusion:.0f}mm from your printer")
    print(f"   📱 Use: Menu → Move Axis → Extruder → {expected_extrusion:.0f}mm")
    leftover = get_float_input("   Enter leftover filament length (e.g., 22.58 mm): ", 
                              min_value=0, max_value=measurement_length, allow_zero=True)    
    actual_extruded = measurement_length - leftover
    new_esteps = old_esteps * (expected_extrusion / actual_extruded)  # ✅ Correct formula
    
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
                                           min_value=MIN_ROTATION_DISTANCE, max_value=50)
    
    print(f"\n{Fore.BLUE}Step 2/4:{Style.RESET_ALL} Set extrusion amount")
    expected_extrusion = get_float_input("   Enter expected extrusion (default: 100mm): ",
                                        min_value=10, max_value=200, default=DEFAULT_EXTRUSION_LENGTH)

    print(f"\n{Fore.BLUE}Step 3/4:{Style.RESET_ALL} Measure and extrude")
    measurement_length = get_float_input(f"   Enter the marked length (mm): ",
                                        min_value=expected_extrusion + 1, max_value=1000)
    print(f"   📏 Mark {measurement_length:.0f}mm from filament inlet")
    print("   ✏️  Mark it with a pen or tape")
    print("   🔥 Heat your hotend to printing temperature")
    print(f"   🎯 Extrude exactly {expected_extrusion:.0f}mm using Klipper command:")
    print(f"   📱 EXTRUDE LENGTH={expected_extrusion:.0f} VELOCITY=5")
    leftover = get_float_input("   Enter leftover filament length (e.g., 22.58 mm): ", 
                              min_value=0, max_value=measurement_length, allow_zero=True)
    actual_extruded = measurement_length - leftover
    new_rot_distance = old_rotation_distance * (actual_extruded / expected_extrusion)  # ✅ Correct Klipper formula

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
    Calibrate flow ratio for Klipper firmware.
    
    Supports two methods:
    1. OrcaSlicer Flow Rate calibration results
    2. Manual wall thickness measurement
    """
    print(f"\n{Fore.YELLOW}=== Flow Ratio Calibration (Klipper) ==={Style.RESET_ALL}")
    print("\nChoose the flow calibration method:")
    print("1. By using OrcaSlicer Flow Measure")
    print("2. 3D Printed Wall Thickness Measure")
    
    method = get_menu_choice(['1', '2'])

    if method == "1":
        print("\nYou can get the Modifier value from the slicer's Flow Rate calibration print.")
        old_flow_ratio = get_float_input("- Enter current flow ratio (e.g., 0.92): ", 
                                        min_value=MIN_FLOW_RATIO, max_value=MAX_FLOW_RATIO)
        modifier = get_float_input("- Enter the flow rate modifier from calibration (e.g., +5 or -3): ", 
                                  min_value=-50, max_value=50, allow_zero=True, allow_negative=True)

        new_flow_ratio = old_flow_ratio * (100 + modifier) / 100  # ✅ Correct formula

    elif method == "2":
        print("\nUsing Wall Thickness Measurement Method")
        print("")
        time.sleep(1)
        print(f"It is advisable to print {Fore.YELLOW}LRGEX flow text v1{Style.RESET_ALL} to measure the wall thickness, or create a cube with 0.4 walls no infill and no top layers")
        old_flow_ratio = get_float_input("- Enter current flow ratio (e.g., 0.92): ", 
                                        min_value=MIN_FLOW_RATIO, max_value=MAX_FLOW_RATIO)
        expected_thickness = get_float_input("- Enter expected wall thickness (e.g., 0.4): ", 
                                           min_value=0.05, max_value=5.0)
        measured_thickness = get_float_input("- Enter measured wall thickness (e.g., 0.36): ", 
                                           min_value=0.05, max_value=5.0)

        new_flow_ratio = old_flow_ratio * (expected_thickness / measured_thickness)
    
    print(f"\n{Fore.GREEN}=== Calibration Results ==={Style.RESET_ALL}")
    print(f"Your new {Fore.GREEN}calibrated flow ratio:{Style.RESET_ALL} {Fore.YELLOW}{new_flow_ratio:.4f}{Style.RESET_ALL}")
    input(CONTINUE_PROMPT)


def calibrate_axis_rotation_distance():
    """
    Calibrate axis rotation distances for Klipper firmware.
    
    This function calculates the correct rotation_distance values for X, Y, and Z axes
    by comparing expected vs measured dimensions of a calibration cube.
    """
    print(f"\n{Fore.YELLOW}=== Klipper Axis Rotation Distance Calibration ==={Style.RESET_ALL}\n")

    expected_x = get_float_input("Enter expected X dimension (default 20mm): ", 
                                min_value=0.1, max_value=500, allow_zero=False, default=DEFAULT_CUBE_SIZE)
    expected_y = get_float_input("Enter expected Y dimension (default 20mm): ", 
                                min_value=0.1, max_value=500, allow_zero=False, default=DEFAULT_CUBE_SIZE)
    expected_z = get_float_input("Enter expected Z dimension (default 20mm): ", 
                                min_value=0.1, max_value=500, allow_zero=False, default=DEFAULT_CUBE_SIZE)

    print("\nMeasure the actual dimensions of the printed calibration cube.")
    measured_x = get_float_input(f"Enter measured{Fore.BLUE} X {Style.RESET_ALL} dimension: ", 
                                min_value=0.1, max_value=500)
    measured_y = get_float_input(f"Enter measured {Fore.BLUE} Y {Style.RESET_ALL} dimension: ", 
                                min_value=0.1, max_value=500)
    measured_z = get_float_input(f"Enter measured{Fore.BLUE} Z {Style.RESET_ALL} dimension: ", 
                                min_value=0.1, max_value=500)

    current_x = get_float_input(f"\n{Fore.CYAN}📍 In printer.cfg, find [stepper_x] section:{Style.RESET_ALL}\nEnter current rotation_distance for X: ", 
                               min_value=MIN_ROTATION_DISTANCE, max_value=MAX_ROTATION_DISTANCE)
    current_y = get_float_input(f"\n{Fore.CYAN}📍 In printer.cfg, find [stepper_y] section:{Style.RESET_ALL}\nEnter current rotation_distance for Y: ", 
                               min_value=MIN_ROTATION_DISTANCE, max_value=MAX_ROTATION_DISTANCE)
    current_z = get_float_input(f"\n{Fore.CYAN}📍 In printer.cfg, find [stepper_z] section:{Style.RESET_ALL}\nEnter current rotation_distance for Z: ", 
                               min_value=MIN_ROTATION_DISTANCE, max_value=MAX_ROTATION_DISTANCE)

    # ✅ Calculate new rotation distances using correct Klipper formula
    new_x = current_x * (measured_x / expected_x)
    new_y = current_y * (measured_y / expected_y)
    new_z = current_z * (measured_z / expected_z)
    
    print(f"\n{Fore.GREEN}=== New Rotation Distance Values (Corrected) ==={Style.RESET_ALL}\n")
    print(f"[stepper_x]\n{Fore.YELLOW}rotation_distance:{Style.RESET_ALL} {new_x:.4f}")
    print(f"[stepper_y]\n{Fore.YELLOW}rotation_distance:{Style.RESET_ALL} {new_y:.4f}")
    print(f"[stepper_z]\n{Fore.YELLOW}rotation_distance:{Style.RESET_ALL} {new_z:.4f}")
    
    print("\nUpdate your 'printer.cfg' file with these values and restart Klipper.")
    input(CONTINUE_PROMPT)

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
    
    print("\n   💧 Flow Ratio (Klipper):")
    print("      Fine-tunes how much plastic is extruded during printing.")
    print("      Fixes over/under-extrusion issues.")
    
    print("\n   📐 Axis Calibration (Klipper):")
    print("      Calibrates X, Y, Z movement accuracy.")
    print("      Ensures printed dimensions match design dimensions.")
    
    print(f"\n{Fore.YELLOW}🎯 Which calibration should I do first?{Style.RESET_ALL}")
    print("   1. Start with E-steps/Rotation Distance")
    print("   2. Then do Flow Ratio calibration") 
    print("   3. Finally, do Axis calibration if needed")
    
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
        print(f"   3. 💧 Calibrate Flow Ratio {Fore.GREEN}(Klipper){Style.RESET_ALL}")
        print(f"   4. 📐 Calibrate Axis Rotation Distance (X, Y, Z) {Fore.GREEN}(Klipper){Style.RESET_ALL}")
        print("   5. ❓ Help & Information")
        print("   6. 🚪 Exit")

        choice = get_menu_choice(['1', '2', '3', '4', '5', '6'])

        if choice == '1':
            calibrate_esteps()
        elif choice == '2':
            calibrate_rotation_distance()
        elif choice == '3':
            calibrate_flow_ratio()
        elif choice == '4':
            calibrate_axis_rotation_distance()
        elif choice == '5':
            show_help()
        elif choice == '6':
            print(f"\n{Fore.GREEN}✨ Thank you for using the 3D Printer Calibration Utility!{Style.RESET_ALL}")
            print("🎯 Happy printing!")
            break
        
        # Ask if user wants to continue
        print(f"\n{Fore.CYAN}{'─'*60}{Style.RESET_ALL}")
        continue_choice = input(f"{Fore.YELLOW}Continue with another calibration? (y/n): {Style.RESET_ALL}").strip().lower()
        if continue_choice in ['n', 'no', 'q', 'quit']:
            print(f"\n{Fore.GREEN}✨ Thank you for using the 3D Printer Calibration Utility!{Style.RESET_ALL}")
            break

if __name__ == "__main__":
    try:
        print(logo)
        time.sleep(2)
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Program interrupted by user. Goodbye!{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}An unexpected error occurred: {e}{Style.RESET_ALL}")
        print("Please report this issue if it persists.")