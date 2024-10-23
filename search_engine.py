import tkinter as tk
from tkinter import scrolledtext, ttk
import requests
import re

# Function to fetch file content from Firebase Storage


def fetch_file_content_from_url(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return f"Failed to fetch file: {response.status_code}"

# Function to search the text file and show the item and its location


def search_file():
    # Get the part number from the entry box
    part_number_query = part_number_entry.get()
    value_query = value_entry.get()  # Get the value from the entry box
    unit_query = unit_entry.get()  # Get the unit from the entry box
    result_box.delete(1.0, tk.END)  # Clear previous item results
    location_box.delete(1.0, tk.END)  # Clear previous location results

    # Update status bar
    status_var.set("Searching...")
    root.update_idletasks()

    # Fetch the file content from the URL
    file_content = fetch_file_content_from_url(file_url)

    if file_content.startswith("Failed to fetch file"):
        result_box.insert(tk.END, file_content)
        status_var.set("Failed to fetch file.")
        return

    # Split the content by lines and search based on input
    lines = file_content.splitlines()

    # Regular expressions for different search fields
    search_patterns = []
    if part_number_query:
        search_patterns.append(re.compile(
            rf'\b{part_number_query}\b', re.IGNORECASE))
    if value_query and unit_query:
        search_patterns.append(re.compile(
            rf'\b{value_query}\s*{unit_query}\b', re.IGNORECASE))
    elif value_query:
        # Less precise if unit is missing
        search_patterns.append(re.compile(
            rf'\b{value_query}\b', re.IGNORECASE))

    matched_items = []
    for pattern in search_patterns:
        matched_items.extend([line for line in lines if pattern.search(line)])

    # Display the results in the result box
    if matched_items:
        for item in matched_items:
            result_box.insert(tk.END, item + '\n')
            # Assuming 'Workshop' is the location for all items
            location_box.insert(tk.END, "Workshop\n")
        status_var.set(f"Search completed. Found {len(matched_items)} items.")
    else:
        result_box.insert(tk.END, "No matches found.\n")
        location_box.insert(tk.END, "No locations available.\n")
        status_var.set("No matches found.")


# Firebase Storage URL
file_url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts.txt?alt=media&token=fa30c0a3-926a-4ee2-b2b1-7b8b1b84876f"

# Set up the main window
root = tk.Tk()
root.title("Component Search Interface")
root.geometry("950x600")  # Adjust the window size
root.config(bg="#f0f0f0")  # Light gray background

# Create a title label
title_label = tk.Label(root, text="Component Search Tool", font=(
    "Helvetica", 16, "bold"), bg="#f0f0f0", fg="#333")
title_label.grid(row=0, column=0, columnspan=2, pady=10, sticky="w")

# Create a label and entry widget for part number input
part_number_label = tk.Label(root, text="Enter part number:", font=(
    "Helvetica", 12), bg="#f0f0f0", fg="#333")
part_number_label.grid(row=1, column=0, pady=2, padx=2, sticky="w")
part_number_entry = ttk.Entry(root, width=20, font=(
    "Helvetica", 12))  # Adjust width if needed
part_number_entry.grid(row=1, column=1, pady=2, padx=2, sticky="w")

# Create a label and entry widget for value input
value_label = tk.Label(root, text="Enter value:", font=(
    "Helvetica", 12), bg="#f0f0f0", fg="#333")
value_label.grid(row=2, column=0, pady=2, padx=2, sticky="w")
value_entry = ttk.Entry(root, width=20, font=(
    "Helvetica", 12))  # Adjust width if needed
value_entry.grid(row=2, column=1, pady=2, padx=2, sticky="w")

# Create a label and entry widget for unit input
unit_label = tk.Label(root, text="Enter unit:", font=(
    "Helvetica", 12), bg="#f0f0f0", fg="#333")
unit_label.grid(row=3, column=0, pady=2, padx=2, sticky="w")
unit_entry = ttk.Entry(root, width=20, font=(
    "Helvetica", 12))  # Adjust width if needed
unit_entry.grid(row=3, column=1, pady=2, padx=2, sticky="w")

# Create a search button with styling
search_button = ttk.Button(root, text="Search", command=search_file)
search_button.grid(row=4, column=0, columnspan=2, pady=10, sticky="w")

# Create a label for "Component"
result_box_label = tk.Label(root, text="Component:", font=(
    "Helvetica", 12, "bold"), bg="#f0f0f0", fg="#555")
result_box_label.grid(row=5, column=0, padx=20, pady=5, sticky="w")

# Create a label for "Location"
location_box_label = tk.Label(root, text="Location:", font=(
    "Helvetica", 12, "bold"), bg="#f0f0f0", fg="#555")
location_box_label.grid(row=5, column=1, padx=20, pady=5, sticky="w")

# Create a scrolled text widget to display search results (items)
result_box = scrolledtext.ScrolledText(root, width=40, height=15, font=(
    "Helvetica", 11), borderwidth=2, relief="solid")
result_box.grid(row=6, column=0, padx=20, pady=10, sticky="w")

# Create a scrolled text widget to display item locations
location_box = scrolledtext.ScrolledText(root, width=40, height=15, font=(
    "Helvetica", 11), borderwidth=2, relief="solid")
location_box.grid(row=6, column=1, padx=20, pady=10, sticky="w")

# Add a status bar with larger text
status_var = tk.StringVar()
status_var.set("Enter part number, value, or unit to begin searching.")
status_bar = tk.Label(root, textvariable=status_var, font=(
    "Helvetica", 12), bg="#e0e0e0", anchor="w", relief="sunken")
status_bar.grid(row=7, column=0, columnspan=2, sticky="we", padx=10, pady=5)

# Run the application
root.mainloop()
