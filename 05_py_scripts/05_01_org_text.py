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
CHUNK_SIZE = 5000   # Number of characters per chunk
MAX_CHUNKS = None   # Set to None to process all chunks
TOTAL_LOCATIONS = 128  # Total available box locations (1 to 128)

# Load API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError(
        "Missing OpenAI API Key. Set OPENAI_API_KEY in your environment variables.")

client = openai.OpenAI(api_key=api_key)

# File paths
input_file = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/04_extracted_info/extracted_texts.txt"
output_file = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/04_extracted_info/organized_texts.txt"

# ------------------------------------------------------------------------------
# Step 1. Read the output file to get already processed image names and assigned locations
# ------------------------------------------------------------------------------
existing_images = set()      # Set of already processed image file names
used_locations = {}          # Dictionary mapping prefix -> set of assigned numbers

if os.path.exists(output_file):
    with open(output_file, "r") as f:
        content = f.read().strip()
        # Each entry is assumed to be separated by double newlines.
        entries = content.split("\n\n")
        for entry in entries:
            # Get image file name from the first line ("Image: <filename>")
            img_match = re.search(r"^Image:\s*(\S+)", entry, re.MULTILINE)
            if img_match:
                existing_images.add(img_match.group(1))
            # Get location if present ("Location: <value>")
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

# ------------------------------------------------------------------------------
# Step 2. Read and filter the input file so that only new entries are processed
# ------------------------------------------------------------------------------
try:
    with open(input_file, "r") as file:
        full_text = file.read().strip()
except FileNotFoundError:
    print(f"Error: File not found at {input_file}")
    exit(1)

if not full_text:
    print("Error: Extracted text file is empty.")
    exit(1)

# Assume each entry starts with a line "Image: <filename>" and entries are separated by two newlines.
all_entries = full_text.split("\n\n")
new_entries_list = []
for entry in all_entries:
    image_match = re.search(r"^Image:\s*(\S+)", entry, re.MULTILINE)
    if image_match:
        image_name = image_match.group(1)
        if image_name not in existing_images:
            new_entries_list.append(entry)
    else:
        # If no image name found, include the entry by default (or skip it)
        new_entries_list.append(entry)

print(
    f"Processing {len(new_entries_list)} new entries out of {len(all_entries)} total entries.")

if not new_entries_list:
    print("No new entries to process. Exiting.")
    exit(0)

# Reassemble new entries into one text blob (separated by double newlines)
new_text_to_process = "\n\n".join(new_entries_list)

# ------------------------------------------------------------------------------
# Step 3. Split the new text into chunks (if needed) and call the OpenAI API
# ------------------------------------------------------------------------------


def extract_data_in_chunks(text, chunk_size=CHUNK_SIZE, max_chunks=MAX_CHUNKS):
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    if max_chunks is not None:
        chunks = chunks[:max_chunks]

    extracted_data = []

    for idx, chunk in enumerate(chunks):
        print(f"Processing chunk {idx + 1}/{len(chunks)}...")

        # Updated prompt: remove location assignment instructions
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
            extracted_data.append(response.choices[0].message.content.strip())
        except Exception as e:
            print(f"Error in OpenAI API call: {e}")
            return None

    return "\n\n".join(extracted_data)


extracted_data = extract_data_in_chunks(new_text_to_process)

# ------------------------------------------------------------------------------
# Step 4. For each new API entry, assign a location considering the 128 box locations limit
# ------------------------------------------------------------------------------


def assign_location(component_type):
    """
    Given a component type string, determine the prefix letter:
      - "C" for capacitor
      - "R" for resistor
      - Otherwise, the first letter of the component type in uppercase.
    Then assign a location sequentially:
      - If some locations are already used for that prefix, assign max(used) + 1 (if available).
      - If no locations are used yet, assign 1.
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

    # If there are already used numbers, try to assign the next sequential number
    if used:
        candidate = max(used) + 1
        if candidate <= TOTAL_LOCATIONS:
            chosen = candidate
        else:
            # If candidate exceeds the limit, fill the lowest available number
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
    # Split by double newlines assuming each entry is separated by an empty line.
    for entry in extracted_data.split("\n\n"):
        # Extract component type (assumed to be on a line starting with "Component Type:")
        comp_match = re.search(r"^Component Type:\s*(.+)", entry, re.MULTILINE)
        component_type = comp_match.group(1).strip() if comp_match else ""
        # Assign a location based on the component type.
        location = assign_location(component_type)
        # Append the location to the entry.
        updated_entry = entry.strip() + f"\nLocation: {location}"
        new_api_entries.append(updated_entry)

    # ------------------------------------------------------------------------------
    # Step 5. Append new unique entries to the output file
    # ------------------------------------------------------------------------------
    # (We already filtered by image names earlier, but verify again)
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
