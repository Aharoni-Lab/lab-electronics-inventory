from google.api_core.exceptions import GoogleAPICallError
import time
import os
from google.cloud import vision
import io
from PIL import Image
import pyheif
from datetime import datetime

# Set Google Cloud Vision API credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/aharonilab-9410614763f1.json"

# Initialize a Vision API client
client = vision.ImageAnnotatorClient()

# Directories and output files
heic_source_directory = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/files/Federico'
converted_image_directory = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/converted_to_jpeg'
base_output_dir = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/'

# Extract the last word (directory name) from the heic_source_directory
last_word = os.path.basename(heic_source_directory)

# Create a unique output file name based on the last word
output_txt_file = f'{base_output_dir}extracted_texts_{last_word}.txt'

# Now output_txt_file will be '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/extracted_texts_Federico.txt'


def load_all_processed_files(base_dir):
    """Load the list of processed file names from all extracted_texts_xxx.txt files."""
    processed_files = set()

    # Get all extracted_texts_*.txt files in the base directory
    for txt_file in os.listdir(base_dir):
        if txt_file.startswith("extracted_texts_") and txt_file.endswith(".txt"):
            txt_output = os.path.join(base_dir, txt_file)
            with open(txt_output, 'r') as f_output:
                for line in f_output:
                    if line.startswith("Image: "):
                        processed_files.add(
                            line.strip().replace("Image: ", ""))

    return processed_files


def append_to_log(log_file, filename):
    """Append a new processed file name to the log."""
    with open(log_file, 'a') as f_log:
        f_log.write(f"{filename}\n")


def convert_heic_to_jpg(heic_directory, jpg_directory, processed_files):
    if not os.path.exists(jpg_directory):
        os.makedirs(jpg_directory)

    processed_count = 0  # Initialize a counter

    for filename in os.listdir(heic_directory):
        if filename.lower().endswith('.heic'):
            jpg_filename = os.path.splitext(filename)[0] + '.jpg'
            if jpg_filename in processed_files:
                print(
                    f"Skipping conversion for {filename}, already processed.")
                continue

            processed_count += 1  # Increment the counter
            heic_path = os.path.join(heic_directory, filename)
            jpg_path = os.path.join(jpg_directory, jpg_filename)

            # Load and convert .heic image
            heif_file = pyheif.read(heic_path)
            image = Image.frombytes(heif_file.mode, heif_file.size,
                                    heif_file.data, "raw", heif_file.mode, heif_file.stride)
            image.save(jpg_path, "JPEG")

            print(f"{processed_count}. Converted {filename} to {jpg_filename}")

    return processed_count  # Return the count of processed images


def extract_text_from_image(image_path):
    retries = 3
    for i in range(retries):
        try:
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            image = vision.Image(content=content)
            response = client.text_detection(image=image)  # Your API call
            return response.full_text_annotation.text  # Return extracted text
        except GoogleAPICallError as e:
            print(f"Error encountered: {e}. Retrying {i + 1}/{retries}...")
            time.sleep(2 ** i)  # Exponential backoff
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break
    return None


def process_images_in_directory(directory, txt_output, processed_files):
    """Process all images in the specified directory and append the extracted texts."""
    with open(txt_output, 'a') as f_output:  # Open the file in append mode
        for filename in os.listdir(directory):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                if filename in processed_files:
                    print(f"Skipping {filename}, already processed.")
                    continue

                image_path = os.path.join(directory, filename)

                # Extract text from the image
                extracted_text = extract_text_from_image(image_path)

                if extracted_text:
                    # Append the extracted text to the .txt file
                    f_output.write(f"Image: {filename}\n")
                    f_output.write(f"Extracted Text:\n{extracted_text}\n\n")

                    print(f"Text from {filename} saved.")


# Load the list of previously processed files from all extracted_texts_xxx.txt files
processed_files = load_all_processed_files(base_output_dir)

# Convert .heic images to .jpg before processing, skipping previously processed files
total_converted = convert_heic_to_jpg(
    heic_source_directory, converted_image_directory, processed_files)

# Process all images and save their text outputs, skipping previously processed files
process_images_in_directory(
    converted_image_directory, output_txt_file, processed_files)

# Print the total number of images processed
print(f"Total images processed: {total_converted}")
