import tkinter as tk
from tkinter import scrolledtext, ttk, simpledialog, messagebox
import requests
import re
import pyrebase

# Firebase config for Authentication and Storage
firebase_config = {
    "apiKey": "AIzaSyAfuAm0ibddHtOn9JdTI3ih7IZO-4XKmeU",
    "authDomain": "aharonilabinventory.firebaseapp.com",
    "databaseURL": "https://aharonilabinventory.firebaseio.com",
    "projectId": "aharonilabinventory",
    "storageBucket": "aharonilabinventory.appspot.com",
    "messagingSenderId": "YOUR_MESSAGING_SENDER_ID",
    "appId": "YOUR_APP_ID",
    "measurementId": "YOUR_MEASUREMENT_ID"
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
storage = firebase.storage()

# Function to log in the user


def login():
    email = simpledialog.askstring("Login", "Enter your email:")
    password = simpledialog.askstring(
        "Password", "Enter your password:", show='*')

    try:
        user = auth.sign_in_with_email_and_password(email, password)
        messagebox.showinfo("Login Success", "You are logged in!")
        return user
    except Exception as e:
        messagebox.showerror("Login Error", "Failed to log in: " + str(e))
        return None

# Function to fetch file content from Firebase Storage


def fetch_file_content():
    try:
        url = storage.child("to_be_ordered.txt").get_url(None)
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            return f"Failed to fetch file: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

# Function to append missing part number and person's name to 'to_be_ordered.txt'


def append_to_order_file(part_number, person_name, user):
    try:
        # Download current content
        current_content = storage.child(
            "to_be_ordered.txt").download().decode()

        # Append the new part number and person's name
        updated_content = current_content + \
            f"Part: {part_number}, Ordered by: {person_name}\n"

        # Upload the updated content
        storage.child("to_be_ordered.txt").put(
            updated_content, user['idToken'])
        print(
            f"Appended 'Part: {part_number}, Ordered by: {person_name}' to 'to_be_ordered.txt'.")
    except Exception as e:
        print(f"Failed to append to file: {str(e)}")

# Function to ask for part number and person's name in a pop-up window


def order_part_popup(user):
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
            append_to_order_file(part_number, person_name, user)
            result_box.insert(
                tk.END, f"Part: '{part_number}' ordered by '{person_name}' has been added to the order list.\n")
            popup.destroy()
        else:
            messagebox.showerror(
                "Input Error", "Both fields must be filled out!")

    submit_button = ttk.Button(popup, text="Submit", command=submit)
    submit_button.grid(row=2, column=0, columnspan=2, pady=10)

    popup.transient(root)
    popup.grab_set()
    root.wait_window(popup)

# Function to search the file content


def search_file(user):
    # Get the part number from the entry box
    part_number_query = part_number_entry.get()
    value_query = value_entry.get()
    unit_query = unit_entry.get()
    result_box.delete(1.0, tk.END)
    location_box.delete(1.0, tk.END)

    status_var.set("Searching...")
    root.update_idletasks()

    file_content = fetch_file_content()
    if file_content.startswith("Failed"):
        result_box.insert(tk.END, file_content)
        status_var.set("Failed to fetch file.")
        return

    lines = file_content.splitlines()
    search_patterns = []

    if part_number_query:
        search_patterns.append(re.compile(
            rf'\b{part_number_query}\b', re.IGNORECASE))
    if value_query and unit_query:
        search_patterns.append(re.compile(
            rf'\b{value_query}\s*{unit_query}\b', re.IGNORECASE))
    elif value_query:
        search_patterns.append(re.compile(
            rf'\b{value_query}\b', re.IGNORECASE))

    matched_items = []
    for pattern in search_patterns:
        matched_items.extend([line for line in lines if pattern.search(line)])

    if matched_items:
        for item in matched_items:
            result_box.insert(tk.END, item + '\n')
            location_box.insert(tk.END, "Workshop\n")
        status_var.set(f"Search completed. Found {len(matched_items)} items.")
    else:
        result_box.insert(tk.END, "No matches found.\n")
        location_box.insert(tk.END, "No locations available.\n")
        status_var.set("No matches found.")
        if messagebox.askyesno("Order Part", "No matches found. Do you want to order this part?"):
            order_part_popup(user)


# Firebase Storage URL
file_url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/to_be_ordered.txt?alt=media&token=fa30c0a3-926a-4ee2-b2b1-7b8b1b84876f"

# Set up the main window
root = tk.Tk()
root.title("Component Search Interface")
root.geometry("950x600")
root.config(bg="#f0f0f0")

# Login the user
user = login()

if user:  # Proceed only if the user is logged in
    # Create the interface after login is successful
    part_number_label = tk.Label(root, text="Enter part number:", font=(
        "Helvetica", 12), bg="#f0f0f0", fg="#333")
    part_number_label.grid(row=1, column=0, pady=2, padx=2, sticky="w")
    part_number_entry = ttk.Entry(root, width=20, font=("Helvetica", 12))
    part_number_entry.grid(row=1, column=1, pady=2, padx=2, sticky="w")

    value_label = tk.Label(root, text="Enter value:", font=(
        "Helvetica", 12), bg="#f0f0f0", fg="#333")
    value_label.grid(row=2, column=0, pady=2, padx=2, sticky="w")
    value_entry = ttk.Entry(root, width=20, font=("Helvetica", 12))
    value_entry.grid(row=2, column=1, pady=2, padx=2, sticky="w")

    unit_label = tk.Label(root, text="Enter unit:", font=(
        "Helvetica", 12), bg="#f0f0f0", fg="#333")
    unit_label.grid(row=3, column=0, pady=2, padx=2, sticky="w")
    unit_entry = ttk.Entry(root, width=20, font=("Helvetica", 12))
    unit_entry.grid(row=3, column=1, pady=2, padx=2, sticky="w")

    search_button = ttk.Button(
        root, text="Search", command=lambda: search_file(user))
    search_button.grid(row=4, column=0, columnspan=2, pady=10, sticky="w")

    result_box_label = tk.Label(root, text="Component:", font=(
        "Helvetica", 12, "bold"), bg="#f0f0f0", fg="#555")
    result_box_label.grid(row=5, column=0, padx=20, pady=5, sticky="w")

    location_box_label = tk.Label(root, text="Location:", font=(
        "Helvetica", 12, "bold"), bg="#f0f0f0", fg="#555")
    location_box_label.grid(row=5, column=1, padx=20, pady=5, sticky="w")

    result_box = scrolledtext.ScrolledText(root, width=40, height=15, font=(
        "Helvetica", 11), borderwidth=2, relief="solid")
    result_box.grid(row=6, column=0, padx=20, pady=10, sticky="w")

    location_box = scrolledtext.ScrolledText(root, width=40, height=15, font=(
        "Helvetica", 11), borderwidth=2, relief="solid")
    location_box.grid(row=6, column=1, padx=20, pady=10, sticky="w")

    status_var = tk.StringVar()
    status_var.set("Enter part number, value, or unit to begin searching.")
    status_bar = tk.Label(root, textvariable=status_var, font=(
        "Helvetica", 12), bg="#e0e0e0", anchor="w", relief="sunken")
    status_bar.grid(row=7, column=0, columnspan=2,
                    sticky="we", padx=10, pady=5)

    root.mainloop()
