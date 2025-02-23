# ================================================================================================
# NOTE:
# This script organizes previously extracted text entries by processing them in chunks,
# using the OpenAI API to extract structured fields (Image, Part number, Manufacturer Part number,
# Fabricated Company, Description, Footprint, and Component Type), assigning a location to each
# entry based on the component type, and appending new unique entries to an output file.
# Finally, it uploads the output file to Firebase Storage.
# Author: Abasalt Bahrami
# ================================================================================================


import os
import openai
import re
import random
from firebase_admin import credentials, storage
import firebase_admin
from google.api_core.exceptions import GoogleAPICallError
import time
from google.cloud import vision
import io
from PIL import Image
import pyheif

# ================================================================================================
# GLOBAL PARAMETERS
# ================================================================================================
CHUNK_SIZE = 5000       # Number of characters per chunk for processing
# Set to None to process all chunks; otherwise, limit to a specific number
MAX_CHUNKS = None
TOTAL_LOCATIONS = 128   # Total available box locations (numbered 1 to 128)

# --------------------------------------------------------------------------------
# Load API Key for OpenAI from environment variable.
# --------------------------------------------------------------------------------
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError(
        "Missing OpenAI API Key. Set OPENAI_API_KEY in your environment variables.")

# Initialize the OpenAI client with the API key.
client = openai.OpenAI(api_key=api_key)

# --------------------------------------------------------------------------------
# File paths for input (extracted texts) and output (organized texts) files.
# --------------------------------------------------------------------------------
input_file = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/04_extracted_info/extracted_texts.txt"
output_file = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/04_extracted_info/organized_texts.txt"

# --------------------------------------------------------------------------------
# Step 1. Read the output file to get already processed image names and assigned locations.
# --------------------------------------------------------------------------------
existing_images = set()      # Set of already processed image file names
# Dictionary mapping prefix (e.g., 'C', 'R') to a set of assigned numbers
used_locations = {}

# If the output file exists, read it to extract previously processed entries.
if os.path.exists(output_file):
    with open(output_file, "r") as f:
        content = f.read().strip()
        # Each entry is assumed to be separated by double newlines.
        entries = content.split("\n\n")
        for entry in entries:
            # Extract the image file name from a line like "Image: <filename>"
            img_match = re.search(r"^Image:\s*(\S+)", entry, re.MULTILINE)
            if img_match:
                existing_images.add(img_match.group(1))
            # Extract the location (e.g., "Location: C1") if present.
            loc_match = re.search(
                r"^Location:\s*([A-Z])(\d+)", entry, re.MULTILINE)
            if loc_match:
                prefix = loc_match.group(1)
                loc_num = int(loc_match.group(2))
                if prefix not in used_locations:
                    used_locations[prefix] = set()
                used_locations[prefix].add(loc_num)

print(f"Found {len(existing_images)} already processed images.")
print(f"Used locations: {used_locations}")

# --------------------------------------------------------------------------------
# Step 2. Read and filter the input file so that only new entries are processed.
# --------------------------------------------------------------------------------
try:
    with open(input_file, "r") as file:
        full_text = file.read().strip()
except FileNotFoundError:
    print(f"Error: File not found at {input_file}")
    exit(1)

if not full_text:
    print("Error: Extracted text file is empty.")
    exit(1)

# Assume each entry starts with "Image: <filename>" and entries are separated by double newlines.
all_entries = full_text.split("\n\n")
new_entries_list = []
for entry in all_entries:
    # Match the image filename from each entry.
    image_match = re.search(r"^Image:\s*(\S+)", entry, re.MULTILINE)
    if image_match:
        image_name = image_match.group(1)
        # Only process entries whose image names are not in the already processed set.
        if image_name not in existing_images:
            new_entries_list.append(entry)
    else:
        # If no image name is found, include the entry by default (or alternatively skip it)
        new_entries_list.append(entry)

print(
    f"Processing {len(new_entries_list)} new entries out of {len(all_entries)} total entries.")

if not new_entries_list:
    print("No new entries to process. Exiting.")
    exit(0)

# Reassemble new entries into one text blob separated by double newlines.
new_text_to_process = "\n\n".join(new_entries_list)

# --------------------------------------------------------------------------------
# Step 3. Split the new text into chunks (if needed) and call the OpenAI API.
# --------------------------------------------------------------------------------


def extract_data_in_chunks(text, chunk_size=CHUNK_SIZE, max_chunks=MAX_CHUNKS):
    """
    Splits the input text into chunks and processes each chunk using the OpenAI API.
    The API extracts structured fields from the text.
    """
    # Split text into chunks of size 'chunk_size'
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    if max_chunks is not None:
        chunks = chunks[:max_chunks]

    extracted_data = []

    for idx, chunk in enumerate(chunks):
        print(f"Processing chunk {idx + 1}/{len(chunks)}...")

        # Construct the prompt to instruct the API to extract the desired fields.
        prompt = f"""Extract the following fields from the text:
Image (as the first line in the format "Image: <filename>"), Part number, Manufacturer Part number, Fabricated Company, Description, Footprint, and Component Type.
Format the output exactly as follows (do not include a Location):

Image: <filename>
Part number: <value>
Manufacturer Part number: <value>
Fabricated Company: <value>
Description: <value>
Footprint: <value>
Component Type: <value>

Process each entry found in the text using the above structure. Do not include any additional formatting or text.

Text:
{chunk}
"""
        try:
            # Make the API call using OpenAI's Chat Completion endpoint.
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts structured data."},
                    {"role": "user", "content": prompt}
                ]
            )
            # Append the response (trimmed) to our extracted_data list.
            extracted_data.append(response.choices[0].message.content.strip())
        except Exception as e:
            print(f"Error in OpenAI API call: {e}")
            return None

    # Combine all the extracted data chunks into one string separated by double newlines.
    return "\n\n".join(extracted_data)


# Call the extraction function on the new text to process.
extracted_data = extract_data_in_chunks(new_text_to_process)

# --------------------------------------------------------------------------------
# Step 4. For each new API entry, assign a location considering the 128 box locations limit.
# --------------------------------------------------------------------------------


def assign_location(component_type):
    """
    Given a component type string, determine the prefix letter:
      - "C" for capacitor
      - "R" for resistor
      - Otherwise, use the first letter of the component type in uppercase.
    Then, assign a location sequentially:
      - If locations are already used for that prefix, assign max(used) + 1 (if available).
      - If no locations are used, assign 1.
      - If max(used)+1 exceeds TOTAL_LOCATIONS, then choose the smallest available number.
    """
    comp = component_type.strip().lower()
    if "capacitor" in comp:
        prefix = "C"
    elif "resistor" in comp:
        prefix = "R"
    else:
        prefix = component_type.strip()[0].upper(
        ) if component_type.strip() else "X"

    used = used_locations.get(prefix, set())

    # Determine the next available location number for the given prefix.
    if used:
        candidate = max(used) + 1
        if candidate <= TOTAL_LOCATIONS:
            chosen = candidate
        else:
            # If the sequential candidate is out of range, choose the smallest available number.
            available = sorted(set(range(1, TOTAL_LOCATIONS + 1)) - used)
            chosen = available[0] if available else None
    else:
        chosen = 1

    if chosen is not None:
        # Update the used_locations dictionary with the newly assigned number.
        if prefix not in used_locations:
            used_locations[prefix] = set()
        used_locations[prefix].add(chosen)
        return f"{prefix}{chosen}"
    else:
        print(f"No available locations for prefix {prefix}")
        return ""


new_api_entries = []
if extracted_data:
    # Split the extracted data by double newlines, assuming each entry is separated by an empty line.
    for entry in extracted_data.split("\n\n"):
        # Extract the component type (line starting with "Component Type:")
        comp_match = re.search(r"^Component Type:\s*(.+)", entry, re.MULTILINE)
        component_type = comp_match.group(1).strip() if comp_match else ""
        # Assign a location based on the component type.
        location = assign_location(component_type)
        # Append the location information to the entry.
        updated_entry = entry.strip() + f"\nLocation: {location}"
        new_api_entries.append(updated_entry)

    # --------------------------------------------------------------------------------
    # Step 5. Append new unique entries to the output file.
    # --------------------------------------------------------------------------------
    # Although we filtered earlier by image names, we verify again here.
    final_entries = []
    for entry in new_api_entries:
        # Extract the image file name from the entry.
        image_match = re.search(r"^Image:\s*(\S+)", entry, re.MULTILINE)
        if image_match:
            image_name = image_match.group(1)
            if image_name not in existing_images:
                final_entries.append(entry)
                existing_images.add(image_name)
        else:
            final_entries.append(entry)

    if final_entries:
        # Append the new entries to the output file, with each entry separated by double newlines.
        with open(output_file, "a") as f:
            f.write("\n\n".join(final_entries) + "\n\n")
        print(f"\nNew unique entries appended to: {output_file}")
    else:
        print("\nNo new unique entries found. Nothing appended.")
else:
    print("\nNo data extracted from API call.")

# ================================================================================================
# Push the "extracted_texts.txt" file to Firebase Storage.
# ================================================================================================
# Path to your Firebase service account key JSON file.
cred_path = '/Users/abasaltbahrami/Desktop/aharonilabinventory-firebase-adminsdk-fu6uk-d6f7531b46.json'

# Initialize the Firebase Admin SDK with the service account if not already initialized.
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        # Your Firebase Storage bucket name
        'storageBucket': 'aharonilabinventory.appspot.com'
    })


def upload_text_file(local_path, firebase_path):
    """
    Uploads a file from the local system to Firebase Storage, overwriting any existing file at the destination.
    """
    bucket = storage.bucket()
    blob = bucket.blob(firebase_path)
    blob.upload_from_filename(local_path)
    print(f"Uploaded {local_path} to Firebase at {firebase_path}")


# Specify the local text file and the destination file path in Firebase Storage.
local_text_file = output_file
# Destination path in Firebase Storage
firebase_file_path = 'extracted_texts.txt'

# Run the upload function to push the file to Firebase.
upload_text_file(local_text_file, firebase_file_path)
