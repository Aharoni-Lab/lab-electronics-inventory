'''

This code extracts text from component images and uploads the extracted data to Firebase.
Once completed, the inventory is automatically updated, and no further action is required.

'''


from firebase_admin import credentials, storage
import firebase_admin
from google.api_core.exceptions import GoogleAPICallError
import time
import os
from google.cloud import vision
import io
from PIL import Image
import pyheif

# Set Google Cloud Vision API credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/abasaltbahrami/Desktop/aharonilab-8a8c472b70e5.json"

# Directories and output file
heic_source_directory = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/01_inventory_original_files'
converted_image_directory = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/03_converted_to_jpeg'
output_txt_file = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/04_extracted_info/extracted_texts.txt'


def load_all_processed_files(output_txt_file):
    """Load the list of processed file names from the output_txt_file."""
    processed_files = set()
    if os.path.exists(output_txt_file):
        with open(output_txt_file, 'r') as f_log:
            for line in f_log:
                if line.startswith("Image: "):
                    filename = line.strip().split(": ")[1]
                    processed_files.add(filename)
    return processed_files


def convert_heic_to_jpg(heic_path, jpg_path):
    """Convert HEIC to JPEG and save."""
    heif_file = pyheif.read(heic_path)
    image = Image.frombytes(heif_file.mode, heif_file.size,
                            heif_file.data, "raw", heif_file.mode, heif_file.stride)
    image.save(jpg_path, "JPEG")


def extract_text_from_image(image_path):
    """Extract text from the image using Vision API."""
    client = vision.ImageAnnotatorClient()  # Initialize client within function
    retries = 3
    for i in range(retries):
        try:
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            image = vision.Image(content=content)
            response = client.text_detection(image=image)
            return response.full_text_annotation.text
        except GoogleAPICallError as e:
            print(f"Error encountered: {e}. Retrying {i + 1}/{retries}...")
            time.sleep(2 ** i)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break
    return None


def process_all_images(directory, txt_output, processed_files, supported_formats=('.heic', '.jpg', '.jpeg', '.png', '.bmp')):
    """Process all supported image formats in each subfolder, save extracted texts, and add location."""
    all_files = [f for f in os.listdir(directory) if f.lower().endswith(
        supported_formats) and f not in processed_files]

    # Extract the folder name (location)
    location = os.path.basename(directory)

    with open(txt_output, 'a') as f_output:
        for filename in all_files:
            file_path = os.path.join(directory, filename)

            # Skip processing if the file is already in processed_files
            if filename in processed_files:
                print(f"Skipping {filename}, already processed.")
                continue

            if filename.lower().endswith('.heic'):
                # Convert to JPG if the format is HEIC
                jpg_filename = os.path.splitext(filename)[0] + '.jpg'
                jpg_path = os.path.join(
                    converted_image_directory, jpg_filename)
                convert_heic_to_jpg(file_path, jpg_path)
                image_path = jpg_path
            else:
                # Use the existing path for non-HEIC formats
                image_path = file_path

            # Add to processed files
            processed_files.add(filename)

            # Extract text from the image
            extracted_text = extract_text_from_image(image_path)
            if extracted_text:
                f_output.write(f"Image: {filename}\n")
                f_output.write(f"Extracted Text:\n{extracted_text}\n")
                f_output.write(f"Location: {location}\n\n")
                print(f"Text from {filename} saved with location {location}.")


def process_all_subfolders(base_source_directory, output_txt_file):
    """Process all HEIC images in subfolders, extract text, and save in a single file."""
    processed_files = load_all_processed_files(output_txt_file)
    for root, _, files in os.walk(base_source_directory):
        if root == base_source_directory or root in heic_source_directory:
            continue  # Skip the base directory and excluded directories
        print(f"Processing folder: {root}")
        process_all_images(root, output_txt_file, processed_files)


# Start processing all subfolders
process_all_subfolders(heic_source_directory, output_txt_file)
