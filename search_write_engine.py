import tkinter as tk
from tkinter import scrolledtext, ttk, simpledialog, messagebox
import requests
import re
import firebase_admin
from firebase_admin import credentials, storage

# Path to your Firebase service account key JSON file
service_account_path = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/aharonilabinventory-firebase-adminsdk-fu6uk-40d1578c31.json'

# Initialize the Firebase Admin SDK
cred = credentials.Certificate(service_account_path)
firebase_admin.initialize_app(cred, {
    # Replace with your Firebase project ID
    'storageBucket': 'aharonilabinventory.appspot.com'
})

# Function to fetch file content from Firebase Storage


def fetch_file_content_from_url(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return f"Failed to fetch file: {response.status_code}"

# Function to append missing part number and person's name to the 'to_be_ordered.txt' file


def append_to_order_file(part_number, person_name):
    # Get a reference to the Firebase Storage bucket
    bucket = storage.bucket()
    blob = bucket.blob('to_be_ordered.txt')

    # Download current content
    try:
        current_content = blob.download_as_text()
    except Exception as e:
        current_content = ""  # If the file doesn't exist or is empty

    # Append the new part number and person's name
    updated_content = current_content + \
        f"Part: {part_number}, Ordered by: {person_name}\n"

    # Upload the updated content
    blob.upload_from_string(updated_content, content_type='text/plain')
    print(
        f"Appended 'Part: {part_number}, Ordered by: {person_name}' to 'to_be_ordered.txt'.")

# Function to ask for part number and person's name in a single pop-up window


def order_part_popup():
    popup = tk.Toplevel(root)
    popup.title("Order Missing Part")

    tk.Label(popup, text="Your Name:").grid(row=0, column=0, padx=10, pady=10)
    tk.Label(popup, text="Part Number:").grid(
        row=1, column=0, padx=10, pady=10)

    name_entry = ttk.Entry(popup, width=25)
    part_entry = ttk.Entry(popup, width=25)

    name_entry.grid(row=0, column=1, padx=10, pady=10)
    part_entry.grid(row=1, column=1, padx=10, pady=10)

    def submit():
        person_name = name_entry.get()
        part_number = part_entry.get()
        if person_name and part_number:
            append_to_order_file(part_number, person_name)
            result_box.insert(
                tk.END, f"Part: '{part_number}' ordered by '{person_name}' has been added to the order list.\n")
            popup.destroy()
        else:
            messagebox.showerror(
                "Input Error", "Both fields must be filled out!")

    submit_button = ttk.Button(popup, text="Submit", command=submit)
    submit_button.grid(row=2, column=0, columnspan=2, pady=10)

    popup.transient(root)  # Keep the pop-up above the main window
    popup.grab_set()       # Make the pop-up modal
    root.wait_window(popup)  # Wait for the window to be closed

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

    # Regex to find part numbers or values + units in the description
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

    # Search for each pattern in lines
    for pattern in search_patterns:
        matched_items.extend([line for line in lines if pattern.search(line)])

    # Filter to show matches with descriptions like "CAP CER" for capacitors or other full descriptions
    if matched_items:
        for item in matched_items:
            if "CAP" in item or "RES" in item:  # Example check for capacitor or resistor
                result_box.insert(tk.END, item + '\n')
                location_box.insert(tk.END, "Workshop\n")
        status_var.set(f"Search completed. Found {len(matched_items)} items.")
    else:
        result_box.insert(tk.END, "No matches found.\n")
        location_box.insert(tk.END, "No locations available.\n")
        status_var.set("No matches found.")

        # Ask if the user wants to order the missing part
        if messagebox.askyesno("Order Part", "No matches found. Do you want to order this part?"):
            order_part_popup()


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
