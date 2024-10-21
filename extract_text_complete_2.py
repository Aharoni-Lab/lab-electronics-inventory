import os
from google.cloud import vision
import io
import re
import pandas as pd
from PIL import Image
import pyheif

# Set Google Cloud Vision API credentials
# Set Google Cloud Vision API credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/aharonilab-9410614763f1.json"

# Initialize a Vision API client
client = vision.ImageAnnotatorClient()

# Directories and output files
heic_source_directory = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/caps_res'
converted_image_directory = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/converted_to_jpeg'
output_txt_file = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/extracted_texts.txt'
output_excel_file = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/extracted_texts_sorted.xlsx'


def convert_heic_to_jpg(heic_directory, jpg_directory):
    """Converts .heic images to .jpg format and saves them in the specified directory."""
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

    if response.error.message:
        raise Exception(
            f"Error during text detection: {response.error.message}")

    texts = response.text_annotations
    if texts:
        return texts[0].description  # Return the extracted text
    else:
        return "No text detected"


def parse_component_info(text):
    """Extract component information like MFG part number, regular part number, type, value, etc."""
    component_info = {}

    # Extract MFG part number (look for MFG P/N:, MFG:, FG:, or similar prefixes)
    mfg_part_number_match = re.search(
        r'(MFG P/N|MFG|FG|MFC|1FG|[A-Z]*FG)[^:]*P/N:\s*([\w-]+)', text)
    if mfg_part_number_match:
        component_info['MFG Part Number'] = mfg_part_number_match.group(2)
    else:
        component_info['MFG Part Number'] = "Not specified"

    # Extract regular part number (look for P/N: followed by the part number)
    part_number_match = re.search(r'P/N:\s*([\w-]+)', text)
    if part_number_match:
        component_info['Part Number'] = part_number_match.group(1)
    else:
        # Fallback: Try to find a string ending with ND that might indicate a part number
        nd_match = re.search(r'([\w-]+ND)', text)
        if nd_match:
            component_info['Part Number'] = nd_match.group(1)
        else:
            component_info['Part Number'] = "Not specified"

    # Extract component type (CAP, RES, etc.)
    if 'CAP CER' in text:
        component_info['Type'] = 'Capacitor'
        component_info['Material'] = 'Ceramic'
    elif 'RES SMD' in text:
        component_info['Type'] = 'Resistor'
    else:
        type_match = re.search(r'CAP\s+(\w+)', text)
        if type_match:
            component_info['Material'] = type_match.group(1)

    # Extract value
    value_match = re.search(r'(\d+(\.\d+)?(K OHM|OHM|UF|PF))', text)
    if value_match:
        value = value_match.group(1).replace(" OHM", "")
        component_info['Value'] = value

    # Extract tolerance
    tolerance_match = re.search(
        r'(\d+% TOLERANCE|\d+\.\d+% TOLERANCE|\d+%|\d+\.\d+%)', text)
    if tolerance_match:
        component_info['Tolerance'] = tolerance_match.group(1)
    else:
        component_info['Tolerance'] = "Not specified"

    # Extract quality (X7R, etc.)
    quality_match = re.search(r'X7R|C0G|Y5V', text)
    if quality_match:
        component_info['Quality'] = quality_match.group(0)

    # Extract manufacturer
    manufacturer_match = re.search(
        r'(MURATA|PANASONIC|TAIYO YUDEN|KEMET)', text)
    if manufacturer_match:
        component_info['Manufacturer'] = manufacturer_match.group(1)

    # Extract footprint
    footprint_match = re.search(
        r'(01005|0201|0402|0603|0805|1206|1210|1812|2220)', text)
    if footprint_match:
        component_info['Footprint'] = footprint_match.group(1)
    else:
        component_info['Footprint'] = "Not specified"

    # Extract quantity (look for 'QTY' or 'Quantity')
    quantity_match = re.search(
        r'(QTY|Quantity)\s*(\d+\.?\d*)', text, re.IGNORECASE)
    if quantity_match:
        component_info['Quantity'] = quantity_match.group(2)
    else:
        component_info['Quantity'] = "Not specified"

    return component_info


def process_images_in_directory(directory, txt_output, excel_output):
    """Process all images in the specified directory and save the extracted texts and organized data."""
    components_list = []

    with open(txt_output, 'w') as f_output:
        for filename in os.listdir(directory):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_path = os.path.join(directory, filename)
                # print(f"Processing {filename}...")

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

    # Sort the DataFrame by Type, Value, Manufacturer, Tolerance, and Footprint
    components_df.sort_values(
        by=['Type', 'Value', 'Manufacturer', 'Tolerance', 'Footprint'], inplace=True)

    # Save the organized data to an Excel file
    components_df.to_excel(excel_output, index=False)
    print(f"Sorted data saved to {excel_output}")


# Convert .heic images to .jpg before processing
convert_heic_to_jpg(heic_source_directory, converted_image_directory)

# Process all images and save their text outputs
process_images_in_directory(
    converted_image_directory, output_txt_file, output_excel_file)
