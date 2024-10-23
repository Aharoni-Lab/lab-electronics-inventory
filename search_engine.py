import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import requests
import re

# Function to fetch file content from Firebase Storage


def fetch_file_content_from_url(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return f"Failed to fetch file: {response.status_code}"

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
        search_patterns.append(re.compile(
            rf'{re.escape(part_number_query)}', re.IGNORECASE))
    if value_query:
        search_patterns.append(re.compile(
            rf'\b{re.escape(value_query)}\b', re.IGNORECASE))

    matched_items = []

    # Iterate over each image block
    for block in blocks:
        # Skip empty blocks
        if not block.strip():
            continue

        # Check if the block contains both the part number and value (if both are provided)
        if all(pattern.search(block) for pattern in search_patterns):
            # Extract part number, description, and image filename
            part_number_match = re.search(
                rf'P/N:\s*(\S+)', block, re.IGNORECASE)
            desc_match = re.search(r'DESC:\s*(.*)', block, re.IGNORECASE)
            image_match = re.search(r'IMG_\d+\.jpg', block)

            part_number = part_number_match.group(
                1) if part_number_match else "Unknown Part Number"
            value = desc_match.group(
                1) if desc_match else "Value not available"
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
