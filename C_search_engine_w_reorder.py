from datetime import datetime  # Import datetime at the beginning
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import re
from firebase_admin import credentials, storage, initialize_app
import firebase_admin
from datetime import datetime

# Firebase initialization
cred_path = '/Users/abasaltbahrami/Desktop/aharonilabinventory-firebase-adminsdk-fu6uk-d6f7531b46.json'
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'aharonilabinventory.appspot.com'
    })


# Function to fetch file content from a single URL
def fetch_file_content():
    url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts.txt?alt=media"

    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return f"Failed to fetch file: {response.status_code}"


# Function to check if a line is a description
def is_description(line):
    description_patterns = [
        r'\bDESC\b', r'\bPart Description\b', r'\bCIC\b', r'\bESC\b',
        r'\bSC\b', r'\bCAP\b', r'\bRES\b', r'\bIC\b', r'\bLED\b',
        r'\bDIODE\b', r'\bMOSFET\b', r'\bREF DES\b', r'\bTEST POINT\b',
        r'\bSCHOTTKY\b', r'\bARRAY\b', r'\bREG LINEAR\b', r'\bPOS ADJ\b',
        r'\bLENS\b', r'\bCHROMA\b', r'\bASPHERE\b', r'\bPRISM\b', r'\bOPTICS\b',
    ]
    description_regex = re.compile(
        '|'.join(description_patterns), re.IGNORECASE)
    return bool(description_regex.search(line))


# Function to open a popup for entering re-order details
def open_reorder_popup():
    # Create a new top-level window
    reorder_popup = tk.Toplevel(root)
    reorder_popup.title("Re-Order Details")

    # Configure the popup window grid
    reorder_popup.grid_columnconfigure(1, weight=1)

    # Create entry fields for part number, description, and requester name
    tk.Label(reorder_popup, text="Part Number:", font=("Helvetica", 12)).grid(
        row=0, column=0, padx=5, pady=5, sticky="w")
    part_number_entry_popup = ttk.Entry(reorder_popup, width=30)
    part_number_entry_popup.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    tk.Label(reorder_popup, text="Description:", font=("Helvetica", 12)).grid(
        row=1, column=0, padx=5, pady=5, sticky="w")
    description_entry_popup = ttk.Entry(reorder_popup, width=30)
    description_entry_popup.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

    tk.Label(reorder_popup, text="Requester Name:", font=("Helvetica", 12)).grid(
        row=2, column=0, padx=5, pady=5, sticky="w")
    requester_name_entry_popup = ttk.Entry(reorder_popup, width=30)
    requester_name_entry_popup.grid(
        row=2, column=1, padx=5, pady=5, sticky="ew")

    # Function to handle the reorder submission
    def submit_reorder():
        part_number = part_number_entry_popup.get().strip()
        description = description_entry_popup.get().strip()
        requester_name = requester_name_entry_popup.get(
        ).strip() or "N/A"  # Default to "N/A" if empty

        # Validate that part number and description are provided
        if not part_number or not description:
            messagebox.showwarning(
                "Incomplete Information", "Please enter both part number and description.")
            return

        # Call the reorder_item function to save the details
        reorder_item(part_number, description, requester_name)
        reorder_popup.destroy()  # Close the popup after submission

    # Add a submit button to the popup
    submit_button = ttk.Button(
        reorder_popup, text="Submit Re-Order", command=submit_reorder)
    submit_button.grid(row=3, column=0, columnspan=2, pady=10)


def search_file():
    # Get the part number and value from the entry boxes
    part_number_query = part_number_entry.get().strip()
    value_query = value_entry.get().strip().lower()
    footprint_query = footprint_entry.get().strip().lower()

    # Clear previous search results
    result_tree.delete(*result_tree.get_children())

    # Update status bar
    status_var.set("Searching...")
    root.update_idletasks()

    # List of patterns for part number and component name/value search
    search_patterns = []
    if part_number_query:
        search_patterns.append(re.compile(
            rf'{re.escape(part_number_query)}(-ND)?', re.IGNORECASE))

    if value_query:
        value_query_cleaned = value_query.replace(" ", "")
        value_query_pattern = ""
        for i in range(len(value_query_cleaned) - 1):
            value_query_pattern += value_query_cleaned[i]
            if (value_query_cleaned[i].isdigit() and value_query_cleaned[i + 1].isalpha()) or \
                    (value_query_cleaned[i].isalpha() and value_query_cleaned[i + 1].isdigit()):
                value_query_pattern += r"\s*"
        value_query_pattern += value_query_cleaned[-1]
        search_patterns.append(re.compile(
            fr'\b{value_query_pattern}\b', re.IGNORECASE))

    if footprint_query:
        search_patterns.append(re.compile(
            rf'\b{re.escape(footprint_query)}\b', re.IGNORECASE))

    def search_in_blocks(blocks):
        for block in blocks:
            if not block.strip():
                continue
            if all(pattern.search(block) for pattern in search_patterns):
                part_number_match = re.search(
                    r'(?:Lot #|P/N|N):\s*([A-Za-z0-9\-\/# ]+)', block, re.IGNORECASE)
                desc_match = re.search(r'DESC:\s*(.*)', block, re.IGNORECASE)
                if not desc_match:
                    block_lines = block.splitlines()
                    for i, line in enumerate(block_lines):
                        if is_description(line):
                            desc_match = line.strip()
                            if "CHROMA" in desc_match.upper() and i + 2 < len(block_lines):
                                desc_match += " " + \
                                    block_lines[i + 1].strip() + \
                                    block_lines[i + 2].strip()
                            break
                location_match = re.search(
                    r'Location:\s*(.*)', block, re.IGNORECASE)
                location = location_match.group(
                    1) if location_match else "Location not available"
                part_number = part_number_match.group(
                    1) if part_number_match else "P/N not detected"
                value = desc_match.group(1) if isinstance(
                    desc_match, re.Match) else desc_match or "Description not available"
                result_tree.insert("", "end", values=(
                    part_number, value, location))

    file_content = fetch_file_content()

    if file_content.startswith("Failed to fetch file"):
        status_var.set("Failed to fetch inventory file.")
    else:
        blocks = file_content.split("Image:")
        search_in_blocks(blocks)

    # Check if no items were found and prompt for reorder
    if not result_tree.get_children():
        status_var.set("No matches found.")
        reorder_prompt = messagebox.askyesno(
            "No Results Found", "No items found matching the search criteria. Would you like to provide re-order details?")
        if reorder_prompt:
            open_reorder_popup()  # Open the popup for re-order details
    else:
        status_message = f"Search completed. Found {len(result_tree.get_children())} items."
        status_var.set(status_message)


# Function to save re-order request to Firebase

# Function to save re-order request to Firebase

def reorder_item(part_number, description, requester_name):
    """Append the re-order request to Firebase Storage."""
    # Get current date and time
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Format the re-order text with date and time included
    re_order_text = f"Date and Time: {current_time}, Part Number: {part_number}, Description: {description}, Requester Name: {requester_name}\n"

    # Access the Firebase Storage bucket
    bucket = storage.bucket()
    blob = bucket.blob('to_be_ordered.txt')

    # Append text to the file in Firebase
    try:
        if blob.exists():
            existing_content = blob.download_as_text()
            re_order_text = existing_content + re_order_text
        blob.upload_from_string(re_order_text)
        messagebox.showinfo("Re-Order", "Re-order request saved successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save re-order request: {e}")


# New function to handle re-order action for the selected item
def handle_reorder():
    selected_item = result_tree.selection()
    if not selected_item:
        messagebox.showwarning(
            "No Selection", "Please select an item to reorder.")
        return

    item_details = result_tree.item(selected_item[0], "values")
    part_number, description, location = item_details

    # Confirm re-order action
    confirm = messagebox.askyesno(
        "Re-Order Confirmation", f"Do you want to reorder '{part_number}'?")
    if confirm:
        reorder_item(part_number, description, location)


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
value_label = tk.Label(root, text="Enter component name/ value:",
                       font=("Helvetica", 12), bg="#f0f0f0", fg="#333")
value_label.grid(row=2, column=0, pady=2, padx=2, sticky="w")
value_entry = ttk.Entry(root, width=20, font=("Helvetica", 12))
value_entry.grid(row=2, column=1, pady=2, padx=2, sticky="w")

# # Add a small comment under the value input
# value_comment_label = tk.Label(root, text="Search with units included, i.e., 22pF", font=(
#     "Helvetica", 10), bg="#f0f0f0", fg="#555")
# value_comment_label.grid(row=3, column=1, padx=2, sticky="w")


footprint_label = tk.Label(root, text="Enter footprint:", font=(
    "Helvetica", 12), bg="#f0f0f0", fg="#333")
footprint_label.grid(row=3, column=0, pady=2, padx=2, sticky="w")
footprint_entry = ttk.Entry(root, width=20, font=("Helvetica", 12))
footprint_entry.grid(row=3, column=1, pady=2, padx=2, sticky="w")


# Create a search button with styling
search_button = ttk.Button(root, text="Search", command=search_file)
search_button.grid(row=4, column=0, columnspan=2, pady=8, sticky="w")

# Create a Treeview to display search results in columns (Part Number, Value, and Location)
columns = ("Part Number", "Value", "Location")
result_tree = ttk.Treeview(root, columns=columns, show="headings", height=10)
result_tree.heading("Part Number", text="Part Number")
result_tree.heading("Value", text="Description")
result_tree.heading("Location", text="Location")
result_tree.column("Part Number", width=200)
result_tree.column("Value", width=300)
result_tree.column("Location", width=100)
result_tree.grid(row=6, column=0, columnspan=2,
                 padx=15, pady=10, sticky="nsew")

# Add a "Re-Order" button with command to handle_reorder
reorder_button = ttk.Button(root, text="Re-Order", command=handle_reorder)
reorder_button.grid(row=5, column=0, columnspan=2, pady=8, sticky="w")

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
