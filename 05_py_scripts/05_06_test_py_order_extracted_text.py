import os
import openai
import re
import pandas as pd
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
CHUNK_SIZE = 5000  # Number of characters per chunk
MAX_CHUNKS = None  # Set to None to process all chunks

# Load API key
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "Missing OpenAI API Key. Set OPENAI_API_KEY in your environment variables.")

client = openai.OpenAI(api_key=api_key)

# File path
file_path = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/04_extracted_info/extracted_texts.txt"

# Read the file
try:
    with open(file_path, "r") as file:
        extracted_text = file.read().strip()
except FileNotFoundError:
    print(f"Error: File not found at {file_path}")
    exit(1)

if not extracted_text:
    print("Error: Extracted text file is empty.")
    exit(1)

# Function to extract part numbers in smaller chunks


def extract_part_numbers_in_chunks(text, chunk_size=CHUNK_SIZE, max_chunks=MAX_CHUNKS):
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    # If max_chunks is None, process all chunks, otherwise, limit to max_chunks
    if max_chunks is not None:
        chunks = chunks[:max_chunks]

    extracted_data = []

    for idx, chunk in enumerate(chunks):
        print(f"Processing chunk {idx + 1}/{len(chunks)}...")

        prompt = f"""Extract part numbers, manufacturer part numbers, descriptions, locations, and footprints from the following text.
        Format the output as:
        
        Part number: <value>
        Manufacturer Part number: <value>
        Description: <value>
        Location: <value>
        Footprint: <value>
        
        Repeat this structure for each entry without any additional formatting like tables or dashes.
        If a manufacturer part number or footprint does not exist, leave it blank.
        
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


# Extract data using configured chunk settings
extracted_data = extract_part_numbers_in_chunks(extracted_text)

# File path for output
output_file = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/04_extracted_info/extracted_part_numbers.txt"

# Read existing file and extract recorded part numbers
existing_entries = set()
if os.path.exists(output_file):
    with open(output_file, "r") as f:
        for line in f.readlines():
            match = re.search(r"Part number: (\S+)", line)
            if match:
                # Store existing part numbers
                existing_entries.add(match.group(1))

# Process and append only new unique entries
if extracted_data:
    new_entries = []
    for entry in extracted_data.split("\n\n"):  # Split by entries
        part_match = re.search(r"Part number: (\S+)", entry)
        mfg_part_match = re.search(r"Manufacturer Part number: (\S*)", entry)
        footprint_match = re.search(r"Footprint: (\S*)", entry)

        part_number = part_match.group(1) if part_match else None
        mfg_part_number = mfg_part_match.group(1) if mfg_part_match else None
        footprint = footprint_match.group(1) if footprint_match else ""

        # Check if part number or manufacturer part number is already recorded
        if part_number and part_number not in existing_entries:
            new_entries.append(entry)
            existing_entries.add(part_number)  # Avoid duplicates

    # Append only new unique data
    if new_entries:
        with open(output_file, "a") as f:  # Use "a" to append
            f.write("\n\n".join(new_entries) + "\n\n")

        print(f"\nNew unique entries appended to: {output_file}")
    else:
        print("\nNo new unique part numbers found. Nothing appended.")
else:
    print("\nNo data extracted.")

# ================================================================================================
# Push the "extracted_part_numbers.txt" file to Firebase
# ================================================================================================

# Path to your Firebase service account key JSON file
cred_path = '/Users/abasaltbahrami/Desktop/aharonilabinventory-firebase-adminsdk-fu6uk-d6f7531b46.json'

# Initialize Firebase Admin SDK with the service account
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'aharonilabinventory.appspot.com'  # Your Firebase Storage bucket
    })


def upload_text_file(local_path, firebase_path):
    """Upload a file to Firebase Storage, overwriting any existing file at the path."""
    bucket = storage.bucket()
    blob = bucket.blob(firebase_path)
    blob.upload_from_filename(local_path)
    print(f"Uploaded {local_path} to Firebase at {firebase_path}")


# Specify the local path and Firebase path
local_text_file = output_file
firebase_file_path = 'extracted_texts.txt'  # File path in Firebase Storage

# Run the upload function
upload_text_file(local_text_file, firebase_file_path)
