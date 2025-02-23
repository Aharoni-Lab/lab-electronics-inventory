# ----------------------------------------------------------------------------------------
# NOTE:
# This script processes HEIC image files by converting them to JPEG and then extracting text from them
# using the Google Cloud Vision API. It checks for previously processed files via an output log file,
# converts any new HEIC files to JPEG, extracts text from the converted images, and appends the results
# to the output file.
# Author: Abasalt Bahrami
# ----------------------------------------------------------------------------------------


import os
import time
from google.cloud import vision
from google.api_core.exceptions import GoogleAPICallError
from PIL import Image
import pillow_heif

# =============== Register HEIC Support ============================================================
# Register pillow-heif so that Pillow can handle HEIC files.
pillow_heif.register_heif_opener()

# =============== Set Google Cloud Credentials =====================================================
# Set the environment variable for your Google Cloud Vision API credentials.
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/abasaltbahrami/Desktop/aharonilab-8a8c472b70e5.json"

# =============== Define Directories and Output File ===============================================
# Define the directory containing the HEIC files, the directory where converted JPEGs will be saved,
# and the output file where extracted texts will be appended.
heic_source_directory = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/01_inventory_original_files'
converted_image_directory = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/03_converted_to_jpeg'
output_txt_file = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/04_extracted_info/extracted_texts.txt'

# Ensure that the directory for JPEG files exists.
os.makedirs(converted_image_directory, exist_ok=True)

# =============== Load Processed Files Function ======================================================


def load_processed_files(output_file):
    """
    Load the list of processed file names from the output file.
    This function reads through the output file and collects names of images that have already been processed.
    """
    processed = set()
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            for line in f:
                if line.startswith("Image: "):
                    filename = line.strip().split("Image: ")[1]
                    processed.add(filename)
    return processed

# =============== Convert HEIC to JPEG Function ========================================================


def convert_heic_to_jpg(heic_path, jpg_path):
    """
    Convert a HEIC file to JPEG using Pillow (with pillow-heif support).
    This function opens a HEIC file and saves it as a JPEG file.
    """
    image = Image.open(heic_path)
    image.save(jpg_path, "JPEG")

# =============== Extract Text from Image Function ===============


def extract_text_from_image(image_path):
    """
    Extract text from the given image using the Google Cloud Vision API.
    This function reads the image, sends it to the Vision API, and returns any detected text.
    """
    client = vision.ImageAnnotatorClient()
    with open(image_path, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    retries = 3
    for i in range(retries):
        try:
            response = client.text_detection(image=image)
            if response.full_text_annotation:
                return response.full_text_annotation.text
            return None
        except GoogleAPICallError as e:
            print(f"Error: {e}. Retrying {i+1}/{retries}...")
            time.sleep(2 ** i)
        except Exception as e:
            print(f"Unexpected error: {e}")
            break
    return None

# =============== Process HEIC Images Function =========================================================


def process_heic_images():
    """
    Process all HEIC files in the source directory:
    - Load the list of already processed files.
    - For each HEIC file that hasn't been processed:
      - Convert it to JPEG.
      - Extract text using the Vision API.
      - Append the results to the output file.
    """
    processed_files = load_processed_files(output_txt_file)

    with open(output_txt_file, 'a') as f_output:
        for filename in os.listdir(heic_source_directory):
            if filename.lower().endswith('.heic'):
                # Skip file if it has already been processed
                if filename in processed_files:
                    print(f"{filename}: Already processed, skipping.")
                    continue

                # Define the full paths for the HEIC and JPEG files
                heic_path = os.path.join(heic_source_directory, filename)
                jpg_filename = os.path.splitext(filename)[0] + '.jpg'
                jpg_path = os.path.join(
                    converted_image_directory, jpg_filename)

                # =============== Convert HEIC to JPEG ===============
                convert_heic_to_jpg(heic_path, jpg_path)

                # =============== Extract Text from JPEG ===============
                extracted_text = extract_text_from_image(jpg_path)
                if extracted_text:
                    f_output.write(f"Image: {filename}\n")
                    f_output.write(f"Extracted Text:\n{extracted_text}\n\n")
                    print(f"{filename}: Converted to JPEG and extracted text.")
                else:
                    print(f"{filename}: Converted to JPEG, but no text was found.")


# =============== Main Execution ===============
if __name__ == '__main__':
    process_heic_images()
