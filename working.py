import time
from colorama import Fore, Style, init

# Initialize colorama (Fixes Windows CMD issues)
init(autoreset=True)

logo = f"""
    __    ____  _____________  __
   / /   / __ \/ ____/ ____/ |/ /
  / /   / /_/ / / __/ __/  |   /
 / /___/ _, _/ /_/ / /___ /   |  
/_____/_/ |_|\____/_____//_/|_|  
                                                            
LRGEX {Fore.BLUE}3D{Style.RESET_ALL} Printers Calculator {Fore.YELLOW}v1.2{Style.RESET_ALL}
"""

def calibrate_esteps():
    old_esteps = float(input("- Enter current E-steps value: "))
    print("\n- Measure 120mm from filament inlet")
    print("- Mark it")
    print("- Extrude 100mm")
    leftover = float(input("- Enter leftover filament length (e.g., 22.58 mm): "))
    
    actual_extruded = 120 - leftover
    new_esteps = old_esteps * (100 / actual_extruded)  # ✅ Correct formula

    print(f"\nYour new calibrated E-steps: {new_esteps:.2f}")
    time.sleep(6)

def calibrate_rotation_distance():
    old_rotation_distance = float(input("- Enter current rotation_distance (get it from printer.cfg): "))
    expected_extrusion = float(input("- Enter expected movement (default: 100mm): ") or 100)  # ✅ Allow dynamic expected value
    print("\n- Measure 120mm from filament inlet")
    print("- Mark it")
    print("- Extrude 100mm")
    leftover = float(input("- Enter leftover filament length (e.g., 22.58 mm): "))
    
    actual_extruded = 120 - leftover
    new_rot_distance = old_rotation_distance * (expected_extrusion / actual_extruded)  # ✅ FIXED formula

    print(f"\nYour new calibrated rotation_distance: {new_rot_distance:.4f}")
    time.sleep(6)


def calibrate_flow_ratio():
    print("\nChoose the flow calibration method:")
    print("1. OrcaSlicer Flow Measure")
    print("2. Wall Thickness Measure")
    method = input("Enter 1 or 2: ")

    if method == "1":
        print("\nYou can get the Modifier value from the slicer's Flow Rate calibration print.")
        old_flow_ratio = float(input("- Enter current flow ratio (e.g., 0.92): "))
        modifier = float(input("- Enter the flow rate modifier from calibration (e.g., +5 or -3): "))

        new_flow_ratio = old_flow_ratio * (100 + modifier) / 100  # ✅ Correct formula

    elif method == "2":
        print("\nUsing Wall Thickness Measurement Method")
        print("")
        time.sleep(1)
        print(f"It is advisable to print {Fore.YELLOW}LRGEX flow text v1{Style.RESET_ALL} to measure the wall thickness.or create a cube with 0.4 walls no infill and no top layers")
        old_flow_ratio = float(input("- Enter current flow ratio (e.g., 0.92): "))
        expected_thickness = float(input("- Enter expected wall thickness (e.g., 0.4): "))
        measured_thickness = float(input("- Enter measured wall thickness (e.g., 0.36): "))

        new_flow_ratio = old_flow_ratio * (expected_thickness / measured_thickness)
    
    else:
        print("Invalid selection. Please enter 1 or 2.")
        return
    
    print(f"\nYour new {Fore.GREEN}calibrated flow ratio:{Style.RESET_ALL} {new_flow_ratio:.4f}")
    time.sleep(6)


def calibrate_axis_rotation_distance():
    print(f"\n{Fore.YELLOW}=== Klipper Axis Rotation Distance Calibration ==={Style.RESET_ALL}\n")

    expected_x = float(input("Enter expected X dimension (default 20mm): ") or 20)
    expected_y = float(input("Enter expected Y dimension (default 20mm): ") or 20)
    expected_z = float(input("Enter expected Z dimension (default 20mm): ") or 20)

    print("\nMeasure the actual dimensions of the printed calibration cube.")
    
    measured_x = float(input(f"Enter measured{Fore.BLUE} X {Style.RESET_ALL} dimension: "))
    measured_y = float(input(f"Enter measured {Fore.BLUE} Y {Style.RESET_ALL} dimension: "))
    measured_z = float(input(f"Enter measured{Fore.BLUE} Z {Style.RESET_ALL} dimension: "))

    current_x = float(input("Enter current rotation_distance for X: "))
    current_y = float(input("Enter current rotation_distance for Y: "))
    current_z = float(input("Enter current rotation_distance for Z: "))    # ✅ FIXED FORMULA to ensure correct results (corrected the inversion)
    new_x = current_x * (expected_x / measured_x)
    new_y = current_y * (expected_y / measured_y)
    new_z = current_z * (expected_z / measured_z)
    time.sleep(1)
    print(f"\n{Fore.GREEN}=== New Rotation Distance Values (Corrected) ==={Style.RESET_ALL}\n")
    time.sleep(1)
    print(f"[stepper_x]\n{Fore.YELLOW}rotation_distance:{Style.RESET_ALL} {new_x:.4f}")
    print(f"[stepper_y]\n{Fore.YELLOW}rotation_distance:{Style.RESET_ALL} {new_y:.4f}")
    print(f"[stepper_z]\n{Fore.YELLOW}rotation_distance:{Style.RESET_ALL} {new_z:.4f}")

    print("\nUpdate your 'printer.cfg' file with these values and restart Klipper.")
    time.sleep(10)

def main():
    while True:
        print(f"\n==== {Fore.YELLOW}3D Printer Calibration Utility{Style.RESET_ALL} ====")
        print(f"1. Calibrate E-steps {Fore.GREEN}(Klipper){Style.RESET_ALL}")
        print(f"2. Calibrate Rotation Distance {Fore.GREEN}(Klipper){Style.RESET_ALL}")
        print(f"3. Calibrate Flow Ratio {Fore.GREEN}(Klipper){Style.RESET_ALL}")
        print(f"4. Calibrate Axis Rotation Distance (X, Y, Z) {Fore.GREEN}(Klipper){Style.RESET_ALL}")
        print("5. Exit")

        choice = input("Enter your choice (1/2/3/4/5): ")

        if choice == '1':
            calibrate_esteps()
        elif choice == '2':
            calibrate_rotation_distance()
        elif choice == '3':
            calibrate_flow_ratio()
        elif choice == '4':
            calibrate_axis_rotation_distance()
        elif choice == '5':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please select 1, 2, 3, 4, or 5.")
        
        print("\n------------------------------\n")

if __name__ == "__main__":
    print(logo)
    time.sleep(2)
    main()