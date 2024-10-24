import re
import requests
from tkinter import scrolledtext
from tkinter import ttk
import tkinter as tk


# Function to fetch file content from a URL
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
        r'\bDESC\b',
        r'\bPart Description\b',
        r'\bCIC\b',
        r'\bESC\b',
        r'\bSC\b',
        r'\bCAP\b',
        r'\bRES\b',
        r'\bIC\b',
        r'\bLED\b',
        r'\bDIODE\b',
        r'\bMOSFET\b',
        r'\bREF DES\b',
        r'\bTEST POINT\b',
        r'\bSCHOTTKY\b',
        r'\bARRAY\b',
        r'\bREG LINEAR\b',
        r'\bPOS ADJ\b',
        # New patterns for optical elements
        r'\bLENS\b',
        r'\bCHROMA\b',
        r'\bASPHERE\b',
        r'\bPRISM\b',
        r'\bOPTICS\b',
    ]

    description_regex = re.compile(
        '|'.join(description_patterns), re.IGNORECASE)
    return bool(description_regex.search(line))

# Function to search the file and show the item, description, and location


def search_file():
    # Get the part number and value from the entry boxes
    part_number_query = part_number_entry.get().strip()
    value_query = value_entry.get().strip()

    # Clear previous search results
    result_tree.delete(*result_tree.get_children())

    # Update status bar
    status_var.set("Searching...")
    root.update_idletasks()

    # Fetch content from all three files (Workshop, Federico, and Marcel)
    workshop_content = fetch_file_content_from_url(workshop_file_url)
    federico_content = fetch_file_content_from_url(federico_file_url)
    marcel_content = fetch_file_content_from_url(marcel_file_url)

    if (workshop_content.startswith("Failed to fetch file") or
        federico_content.startswith("Failed to fetch file") or
            marcel_content.startswith("Failed to fetch file")):
        status_var.set("Failed to fetch one or more files.")
        return

    # Split content by image blocks
    workshop_blocks = workshop_content.split("Image:")
    federico_blocks = federico_content.split("Image:")
    marcel_blocks = marcel_content.split("Image:")

    search_patterns = []
    if part_number_query:
        # Add pattern for part numbers with or without "-ND" suffix
        search_patterns.append(re.compile(
            rf'{re.escape(part_number_query)}(-ND)?', re.IGNORECASE))
    if value_query:
        search_patterns.append(re.compile(
            rf'\b{re.escape(value_query)}\b', re.IGNORECASE))

    # List of common footprints to search for if DESC is missing
    footprint_patterns = re.compile(
        r'\b(0201|0402|0603|0805|1206|1210|1812|2220)\b')

    def search_in_blocks(blocks, location):
        for block in blocks:
            if not block.strip():
                continue

            # Check if the block contains both the part number and value (if both are provided)
            if all(pattern.search(block) for pattern in search_patterns):
                # Extract part number
                part_number_match = re.search(
                    r'(?:Lot #|P/N|N):\s*([A-Za-z0-9\-\/# ]+)', block, re.IGNORECASE)

                # Try to find description
                desc_match = re.search(r'DESC:\s*(.*)', block, re.IGNORECASE)
                if not desc_match:
                    block_lines = block.splitlines()
                    for line in block_lines:
                        if is_description(line):
                            desc_match = line.strip()
                            break

                # Extract image name
                image_match = re.search(r'IMG_\d+\.jpg', block)
                part_number = part_number_match.group(
                    1) if part_number_match else "Unknown Part Number"
                value = desc_match if isinstance(desc_match, str) else (
                    desc_match.group(1) if desc_match else "Description not available")
                image_name = image_match.group(
                    0) if image_match else "Unknown Image"

                # Add result to the Treeview
                result_tree.insert("", "end", values=(
                    part_number, value, location))

    # Search in Workshop, Federico, and Marcel blocks
    search_in_blocks(workshop_blocks, "Workshop")
    search_in_blocks(federico_blocks, "Federico")
    search_in_blocks(marcel_blocks, "Marcel")

    # Update status bar based on results
    if result_tree.get_children():
        status_var.set(
            f"Search completed. Found {len(result_tree.get_children())} items.")
    else:
        status_var.set("No matches found.")


# Firebase Storage URLs for Workshop, Federico, and Marcel
workshop_file_url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts_Workshop.txt?alt=media&token=4c67ff8b-f207-4fec-b585-c007518bb976"
federico_file_url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts_Federico.txt?alt=media&token=ee37dbb4-44c8-4a82-8ceb-7c9ce8859688"
marcel_file_url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts_Marcel.txt?alt=media&token=0e9da0d2-8f8f-451d-9108-4e2283634894"

# Set up the main window
root = tk.Tk()
root.title("Component Search Interface")
root.config(bg="#f0f0f0")

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
value_label = tk.Label(root, text="Enter component name/ value:", font=(
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