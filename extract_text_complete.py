import os
from google.cloud import vision
import io
import re
import pandas as pd
from PIL import Image
import pyheif

# Set Google Cloud Vision API credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/abasaltbahrami/Desktop/test/aharonilab-9410614763f1.json"

# Initialize a Vision API client
client = vision.ImageAnnotatorClient()

# Directories and output files
heic_source_directory = '/Users/abasaltbahrami/Desktop/test/component_photos'
converted_image_directory = '/Users/abasaltbahrami/Desktop/test/converted_to_jpeg'
output_txt_file = '/Users/abasaltbahrami/Desktop/test/extracted_texts.txt'
output_excel_file = '/Users/abasaltbahrami/Desktop/test/extracted_texts_sorted.xlsx'


def convert_heic_to_jpg(heic_directory, jpg_directory):
    if not os.path.exists(jpg_directory):
        os.makedirs(jpg_directory)

    for filename in os.listdir(heic_directory):
        if filename.lower().endswith('.heic'):
            heic_path = os.path.join(heic_directory, filename)
            jpg_filename = os.path.splitext(filename)[0] + '.jpg'
            jpg_path = os.path.join(jpg_directory, jpg_filename)

            # Load and convert .heic image
            heif_file = pyheif.read(heic_path)
            image = Image.frombytes(heif_file.mode, heif_file.size,
                                    heif_file.data, "raw", heif_file.mode, heif_file.stride)
            image.save(jpg_path, "JPEG")

            print(f"Converted {filename} to {jpg_filename}")


def extract_text_from_image(image_path):
    """Function to extract text from an image using Google Cloud Vision API."""
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    response = client.text_detection(image=image)

    texts = response.text_annotations
    if texts:
        return texts[0].description  # Return the extracted text
    else:
        return "No text detected"

    if response.error.message:
        raise Exception(
            f"Error during text detection: {response.error.message}")


def parse_component_info(text):
    """Extract component information like type, value, tolerance, company, etc."""
    component_info = {}

    # Extract part number
    part_number_match = re.search(r'P/N: ([\w-]+)', text)
    if part_number_match:
        component_info['Part Number'] = part_number_match.group(1)

    # Extract component type (CAP, RES, etc.)
    if 'CAP CER' in text:
        component_info['Type'] = 'Capacitor'
    elif 'RES SMD' in text:
        component_info['Type'] = 'Resistor'

    # Extract value
    value_match = re.search(r'DESC .* (\d+(\.\d+)?(UF|PF|K OHM|OHM))', text)
    if value_match:
        component_info['Value'] = value_match.group(1)

    # Extract tolerance (if available)
    tolerance_match = re.search(r'(\d+% TOLERANCE)', text)
    if tolerance_match:
        component_info['Tolerance'] = tolerance_match.group(1)

    # Extract manufacturer (example: MURATA, PANASONIC, etc.)
    manufacturer_match = re.search(r'(MURATA|PANASONIC|TAIYO YUDEN)', text)
    if manufacturer_match:
        component_info['Manufacturer'] = manufacturer_match.group(1)

    return component_info


def process_images_in_directory(directory, txt_output, excel_output):
    """Process all images in the specified directory and save the extracted texts and organized data."""
    components_list = []

    with open(txt_output, 'w') as f_output:
        for filename in os.listdir(directory):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_path = os.path.join(directory, filename)
                print(f"Processing {filename}...")

                # Extract text from the image
                extracted_text = extract_text_from_image(image_path)

                # Save the extracted text to the .txt file
                f_output.write(f"Image: {filename}\n")
                f_output.write(f"Extracted Text:\n{extracted_text}\n\n")

                # Parse the extracted text
                component_info = parse_component_info(extracted_text)
                # Add image filename for reference
                component_info['Image'] = filename
                components_list.append(component_info)

                print(f"Text from {filename} saved and parsed.")

    # Convert the list of components to a DataFrame
    components_df = pd.DataFrame(components_list)

    # Sort the DataFrame by Type, Value, and Manufacturer
    components_df.sort_values(
        by=['Type', 'Value', 'Manufacturer'], inplace=True)

    # Save the organized data to an Excel file
    components_df.to_excel(excel_output, index=False)
    print(f"Sorted data saved to {excel_output}")


# Convert .heic images to .jpg before processing
convert_heic_to_jpg(heic_source_directory, converted_image_directory)

# Process all images and save their text outputs
process_images_in_directory(
    converted_image_directory, output_txt_file, output_excel_file)
