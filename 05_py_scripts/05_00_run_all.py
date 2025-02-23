import subprocess
import time
import os

# ANSI escape codes for green and reset (normal)
GREEN = "\033[32m"
RESET = "\033[0m"

# Directory where all the scripts are located:
SCRIPTS_DIR = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/05_py_scripts"

scripts = [
    "05_01_ext_txt_from_photos.py",
    "05_02_org_text_update_inv.py",
    "05_03_label_print_storage_box.py",
    "05_04_check_file_counts.py",
    "05_05_firebase_order_check.py"
]

for script in scripts:
    # Define divider line
    divider = "============================================================================="

    # Print divider and header in green
    print(f"{GREEN}{divider}")
    print(f"Running script: {script}")
    print(f"{divider}{RESET}")

    # Build the full path to the script
    full_path = os.path.join(SCRIPTS_DIR, script)

    # Run the script
    subprocess.run(["python", full_path], check=True)

    # Wait for 1 second before proceeding to the next script
    time.sleep(1)
