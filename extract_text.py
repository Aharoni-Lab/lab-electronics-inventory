from google.api_core.exceptions import GoogleAPICallError
import time
import os
from google.cloud import vision
import io
import pandas as pd
from PIL import Image
import pyheif

# Set Google Cloud Vision API credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/aharonilab-9410614763f1.json"

# Initialize a Vision API client
client = vision.ImageAnnotatorClient()

# Directories and output files
heic_source_directory = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/files'
converted_image_directory = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/converted_to_jpeg'
output_txt_file = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/extracted_texts.txt'


def convert_heic_to_jpg(heic_directory, jpg_directory):
    if not os.path.exists(jpg_directory):
        os.makedirs(jpg_directory)

    processed_count = 0  # Initialize a counter

    for filename in os.listdir(heic_directory):
        if filename.lower().endswith('.heic'):
            processed_count += 1  # Increment the counter
            heic_path = os.path.join(heic_directory, filename)
            jpg_filename = os.path.splitext(filename)[0] + '.jpg'
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


def process_images_in_directory(directory, txt_output):
    """Process all images in the specified directory and save the extracted texts."""
    with open(txt_output, 'w') as f_output:
        for filename in os.listdir(directory):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_path = os.path.join(directory, filename)

                # Extract text from the image
                extracted_text = extract_text_from_image(image_path)

                # Save the extracted text to the .txt file
                f_output.write(f"Image: {filename}\n")
                f_output.write(f"Extracted Text:\n{extracted_text}\n\n")

                print(f"Text from {filename} saved.")


# Convert .heic images to .jpg before processing
total_converted = convert_heic_to_jpg(
    heic_source_directory, converted_image_directory)

# Process all images and save their text outputs
process_images_in_directory(converted_image_directory, output_txt_file)

# Print the total number of images processed
print(f"Total images processed: {total_converted}")
