# ================================================================================================
# NOTE:
# This script organizes previously extracted text entries by processing them in chunks,
# using the OpenAI API to extract structured fields (Image, Part number, Manufacturer Part number,
# Fabricated Company, Description, Footprint, and Component Type), assigning a location to each
# entry based on the component type, and appending new unique entries to an output file.
# Finally, it uploads the output file to Firebase Storage.
# Author: Abasalt Bahrami (Modified by You)
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
    image_match = re.search(r"^Image:\s*(\S+)", entry, re.MULTILINE)
    if image_match:
        image_name = image_match.group(1)
        if image_name not in existing_images:
            new_entries_list.append(entry)
    else:
        new_entries_list.append(entry)

print(
    f"Processing {len(new_entries_list)} new entries out of {len(all_entries)} total entries.")

# Instead of exiting when there are no new entries, we continue to duplicate check.
if new_entries_list:
    new_text_to_process = "\n\n".join(new_entries_list)

    # --------------------------------------------------------------------------------
    # Step 3. Split the new text into chunks (if needed) and call the OpenAI API.
    # --------------------------------------------------------------------------------
    def extract_data_in_chunks(text, chunk_size=CHUNK_SIZE, max_chunks=MAX_CHUNKS):
        """
        Splits the input text into chunks and processes each chunk using the OpenAI API.
        The API extracts structured fields from the text.
        """
        chunks = [text[i:i+chunk_size]
                  for i in range(0, len(text), chunk_size)]
        if max_chunks is not None:
            chunks = chunks[:max_chunks]

        extracted_data = []

        for idx, chunk in enumerate(chunks):
            print(f"Processing chunk {idx + 1}/{len(chunks)}...")

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
                response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that extracts structured data."},
                        {"role": "user", "content": prompt}
                    ]
                )
                extracted_data.append(
                    response.choices[0].message.content.strip())
            except Exception as e:
                print(f"Error in OpenAI API call: {e}")
                return None

        return "\n\n".join(extracted_data)

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
        if used:
            candidate = max(used) + 1
            if candidate <= TOTAL_LOCATIONS:
                chosen = candidate
            else:
                available = sorted(set(range(1, TOTAL_LOCATIONS + 1)) - used)
                chosen = available[0] if available else None
        else:
            chosen = 1

        if chosen is not None:
            if prefix not in used_locations:
                used_locations[prefix] = set()
            used_locations[prefix].add(chosen)
            return f"{prefix}{chosen}"
        else:
            print(f"No available locations for prefix {prefix}")
            return ""

    new_api_entries = []
    if extracted_data:
        for entry in extracted_data.split("\n\n"):
            comp_match = re.search(
                r"^Component Type:\s*(.+)", entry, re.MULTILINE)
            component_type = comp_match.group(1).strip() if comp_match else ""
            location = assign_location(component_type)
            updated_entry = entry.strip() + f"\nLocation: {location}"
            new_api_entries.append(updated_entry)

        # --------------------------------------------------------------------------------
        # Step 5. Append new unique entries to the output file.
        # --------------------------------------------------------------------------------
        final_entries = []
        for entry in new_api_entries:
            image_match = re.search(r"^Image:\s*(\S+)", entry, re.MULTILINE)
            if image_match:
                image_name = image_match.group(1)
                if image_name not in existing_images:
                    final_entries.append(entry)
                    existing_images.add(image_name)
            else:
                final_entries.append(entry)

        if final_entries:
            with open(output_file, "a") as f:
                f.write("\n\n".join(final_entries) + "\n\n")
            print(f"\nNew unique entries appended to: {output_file}")
        else:
            print("\nNo new unique entries found. Nothing appended.")
    else:
        print("\nNo data extracted from API call.")
else:
    print("No new entries to process.")

# --------------------------------------------------------------------------------
# Duplicate Check: Scan the entire output file for duplicate Part numbers or Manufacturer Part numbers.
# If duplicates are found, update their locations to be the same.
# --------------------------------------------------------------------------------
print("\nChecking for duplicate entries in the entire output file:")

with open(output_file, "r") as f:
    full_output_text = f.read().strip()

all_output_entries = full_output_text.split("\n\n")
part_dict = {}
manuf_dict = {}

# Build dictionaries mapping part numbers to list of entry indices
for idx, entry in enumerate(all_output_entries):
    part_match = re.search(r"^Part number:\s*(.+)", entry, re.MULTILINE)
    if part_match:
        part_val = part_match.group(1).strip()
        part_dict.setdefault(part_val, []).append(idx)
    manuf_match = re.search(
        r"^Manufacturer Part number:\s*(.+)", entry, re.MULTILINE)
    if manuf_match:
        manuf_val = manuf_match.group(1).strip()
        manuf_dict.setdefault(manuf_val, []).append(idx)

duplicate_found = False

# Process duplicate groups for Part number
for part, indices in part_dict.items():
    if len(indices) > 1:
        duplicate_found = True
        print(f"\nDuplicate entries for Part number: {part}")
        # Use the location from the first occurrence as the unified location
        first_entry = all_output_entries[indices[0]]
        loc_match = re.search(r"^Location:\s*(.+)", first_entry, re.MULTILINE)
        if loc_match:
            unified_location = loc_match.group(1).strip()
            for idx in indices:
                print(all_output_entries[idx])
                print("--------------------------------------------------")
                all_output_entries[idx] = re.sub(
                    r"^(Location:\s*).+",
                    f"\\1{unified_location}",
                    all_output_entries[idx],
                    flags=re.MULTILINE,
                )

# Process duplicate groups for Manufacturer Part number
for manuf, indices in manuf_dict.items():
    if len(indices) > 1:
        duplicate_found = True
        print(f"\nDuplicate entries for Manufacturer Part number: {manuf}")
        first_entry = all_output_entries[indices[0]]
        loc_match = re.search(r"^Location:\s*(.+)", first_entry, re.MULTILINE)
        if loc_match:
            unified_location = loc_match.group(1).strip()
            for idx in indices:
                print(all_output_entries[idx])
                print("--------------------------------------------------")
                all_output_entries[idx] = re.sub(
                    r"^(Location:\s*).+",
                    f"\\1{unified_location}",
                    all_output_entries[idx],
                    flags=re.MULTILINE,
                )

if not duplicate_found:
    print("No duplicate entries found based on Part number or Manufacturer Part number.")
else:
    # Write the updated entries back to the output file
    with open(output_file, "w") as f:
        f.write("\n\n".join(all_output_entries) + "\n\n")
    print("\nDuplicate locations updated in the output file.")

# ================================================================================================
# Push the "extracted_texts.txt" file to Firebase Storage.
# ================================================================================================
cred_path = '/Users/abasaltbahrami/Desktop/aharonilabinventory-firebase-adminsdk-fu6uk-d6f7531b46.json'

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
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


local_text_file = output_file
firebase_file_path = 'extracted_texts.txt'
upload_text_file(local_text_file, firebase_file_path)
