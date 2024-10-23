import re
import requests
from tkinter import scrolledtext
from tkinter import ttk
import tkinter as tk


# Function to fetch file content from Firebase Storage


def fetch_file_content_from_url(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return f"Failed to fetch file: {response.status_code}"

# Function to check if a line is a description


def is_description(line):
    """
    Identifies if a line is likely a component description based on common patterns.
    """
    description_patterns = [
        r'\bDESC\b',                 # Matches 'DESC' or 'DESC:' at the beginning
        r'\bPart Description\b',      # Matches 'Part Description'
        r'\bCIC\b',                  # Matches 'CIC'
        r'\bESC\b',                  # Matches 'ESC' in descriptions like 'ESC CAP'
        r'\bSC\b',                   # Matches 'SC'
        r'\bCAP\b',                  # Matches 'CAP' for capacitors
        r'\bRES\b',                  # Matches 'RES' for resistors
        r'\bIC\b',                   # Matches 'IC' for integrated circuits
        r'\bLED\b',                  # Matches 'LED'
        r'\bDIODE\b',                # Matches 'DIODE'
        r'\bMOSFET\b',               # Matches 'MOSFET'
        r'\bREF DES\b',              # Matches 'REF DES' for specific components
        r'\bTEST POINT\b',           # Matches 'TEST POINT' for test points
        r'\bSCHOTTKY\b',             # Matches 'SCHOTTKY' for diode descriptions
        r'%',                        # Matches the '%' sign in the description
        r'\bARRAY\b',                # Matches 'ARRAY', commonly used for diodes and MOSFETs
        r'\bREG LINEAR\b',           # Matches 'REG LINEAR' for regulators
        r'\bPOS ADJ\b',              # Matches 'POS ADJ' for adjustable components

    ]

    description_regex = re.compile(
        '|'.join(description_patterns), re.IGNORECASE)
    return bool(description_regex.search(line))

# Function to search the text file and show the item, description, and location


# Function to search the text file and show the item, description, and location
def search_file():
    # Get the part number and value from the entry boxes
    part_number_query = part_number_entry.get().strip()
    value_query = value_entry.get().strip()  # Get the value from the entry box

    # Clear previous search results
    result_tree.delete(*result_tree.get_children())

    # Update status bar
    status_var.set("Searching...")
    root.update_idletasks()

    # Fetch the file content from the URL
    file_content = fetch_file_content_from_url(file_url)

    if file_content.startswith("Failed to fetch file"):
        status_var.set("Failed to fetch file.")
        return

    # Split the content by image blocks
    blocks = file_content.split("Image:")  # Split by each image block

    search_patterns = []
    if part_number_query:
        # Add pattern for part numbers with or without "-ND" suffix
        search_patterns.append(re.compile(
            rf'{re.escape(part_number_query)}(-ND)?', re.IGNORECASE))
    if value_query:
        search_patterns.append(re.compile(
            rf'\b{re.escape(value_query)}\b', re.IGNORECASE))

    matched_items = []

    # List of common footprints to search for if DESC is missing
    footprint_patterns = re.compile(
        r'\b(0201|0402|0603|0805|1206|1210|1812|2220)\b')

    # Iterate over each image block
    for block in blocks:
        # Skip empty blocks
        if not block.strip():
            continue

        # Check if the block contains both the part number and value (if both are provided)
        if all(pattern.search(block) for pattern in search_patterns):

            # Extract part number (supporting both 'P/N:' and 'N:' with full part number)
            part_number_match = re.search(
                r'(?:P/N|N):\s*([A-Za-z0-9\-]+)', block, re.IGNORECASE)

            # Try to find description
            desc_match = re.search(r'DESC:\s*(.*)', block, re.IGNORECASE)

            # If DESC is not found, look for a line that ends with the footprint and treat that line as the description
            if not desc_match:
                block_lines = block.splitlines()
                for line in block_lines:
                    if is_description(line):  # Use the is_description function
                        desc_match = line.strip()  # Capture the entire line as the description
                        break

            # Extract image name
            image_match = re.search(r'IMG_\d+\.jpg', block)

            part_number = part_number_match.group(
                1) if part_number_match else "Unknown Part Number"

            # Use description or the entire line as value
            value = desc_match if isinstance(desc_match, str) else (
                desc_match.group(1) if desc_match else "Description not available")

            image_name = image_match.group(
                0) if image_match else "Unknown Image"
            location = "Workshop"  # Assuming location is 'Workshop'

            # Add the result to the Treeview
            result_tree.insert("", "end", values=(
                part_number, value, location))

    # Update status bar based on results
    if result_tree.get_children():
        status_var.set(
            f"Search completed. Found {len(result_tree.get_children())} items.")
    else:
        status_var.set("No matches found.")


# Firebase Storage URL

file_url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts.txt?alt=media&token=fa30c0a3-926a-4ee2-b2b1-7b8b1b84876f"

# Set up the main window
root = tk.Tk()
root.title("Component Search Interface")
root.config(bg="#f0f0f0")  # Light gray background

# Create a title label
title_label = tk.Label(root, text="Component Search Tool", font=(
    "Helvetica", 16, "bold"), bg="#f0f0f0", fg="#333")
title_label.grid(row=0, column=0, columnspan=2, pady=8, sticky="w")

# Create a label and entry widget for part number input
part_number_label = tk.Label(root, text="Enter part number:", font=(
    "Helvetica", 12), bg="#f0f0f0", fg="#333")
part_number_label.grid(row=1, column=0, pady=2, padx=2, sticky="w")
part_number_entry = ttk.Entry(root, width=20, font=("Helvetica", 12))
part_number_entry.grid(row=1, column=1, pady=2, padx=2, sticky="w")

# Create a label and entry widget for value input
value_label = tk.Label(root, text="Enter value:", font=(
    "Helvetica", 12), bg="#f0f0f0", fg="#333")
value_label.grid(row=2, column=0, pady=2, padx=2, sticky="w")
value_entry = ttk.Entry(root, width=20, font=("Helvetica", 12))
value_entry.grid(row=2, column=1, pady=2, padx=2, sticky="w")

# Add a small comment under the value input
value_comment_label = tk.Label(root, text="Search with units included, i.e., 22pF", font=(
    "Helvetica", 10), bg="#f0f0f0", fg="#555")
value_comment_label.grid(row=3, column=1, padx=2, sticky="w")

# Create a search button with styling
search_button = ttk.Button(root, text="Search", command=search_file)
search_button.grid(row=4, column=0, columnspan=2, pady=8, sticky="w")

# Create a Treeview to display search results in columns (Part Number, Value, and Location)
columns = ("Part Number", "Value", "Location")
result_tree = ttk.Treeview(root, columns=columns, show="headings", height=10)
result_tree.heading("Part Number", text="Part Number")
result_tree.heading("Value", text="Value")
result_tree.heading("Location", text="Location")
result_tree.column("Part Number", width=200)
result_tree.column("Value", width=300)
result_tree.column("Location", width=200)
result_tree.grid(row=6, column=0, columnspan=2,
                 padx=15, pady=10, sticky="nsew")

# Add a status bar with larger text
status_var = tk.StringVar()
status_var.set("Enter part number or value to begin searching.")
status_bar = tk.Label(root, textvariable=status_var, font=(
    "Helvetica", 12), bg="#e0e0e0", anchor="w", relief="sunken")
status_bar.grid(row=7, column=0, columnspan=2, sticky="we", padx=8, pady=5)

# Adjust the window to fit all widgets
root.update_idletasks()
root.geometry(f"{root.winfo_width()}x{root.winfo_height()}")

# Run the application
root.mainloop()
