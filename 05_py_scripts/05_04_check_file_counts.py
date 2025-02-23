"""
# NOTE: This script compares image filenames already processed (as listed in a text file)
# with all image files found in a specified directory (and its subdirectories).
# It prints the total number of images in the directory, the number of processed images,
# and any images that are missing from the processed list.
"""

import os
import re

# ----------------------------------------------------------------------------------------
# Define paths for the processed text file and the inventory directory.
# ----------------------------------------------------------------------------------------
processed_text_file_path = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/04_extracted_info/organized_texts.txt'
directory_path = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/01_inventory_original_files'

# ----------------------------------------------------------------------------------------
# Function to extract processed image filenames from the text file.
# ----------------------------------------------------------------------------------------


def get_processed_images(file_path):
    processed_files = set()
    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith("Image: "):
                filename = line.strip().split(": ")[1]
                processed_files.add(filename)
    return processed_files

# ----------------------------------------------------------------------------------------
# Function to retrieve all image files in the directory (and subdirectories)
# with their relative paths.
# ----------------------------------------------------------------------------------------


def get_all_image_files(directory_path):
    image_extensions = {'.heic', '.jpg',
                        '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
    all_files = {}
    for root, _, files in os.walk(directory_path):
        for file in files:
            if os.path.splitext(file.lower())[1] in image_extensions:
                relative_path = os.path.relpath(
                    os.path.join(root, file), directory_path)
                all_files[file] = relative_path
    return all_files


# ----------------------------------------------------------------------------------------
# Run functions to collect data and compare processed images with available images.
# ----------------------------------------------------------------------------------------
all_image_files = get_all_image_files(directory_path)
processed_image_files = get_processed_images(processed_text_file_path)

print(f"Number of images in directory: {len(all_image_files)}")
print(f"Number of images processed: {len(processed_image_files)}")

# ----------------------------------------------------------------------------------------
# Identify and list missing image files.
# ----------------------------------------------------------------------------------------
missing_files = set(all_image_files.keys()) - processed_image_files
if missing_files:
    print("Some files are missing in the processed text file.")
    print("Missing files:")
    for file in missing_files:
        print(f"{file} (Subfolder: {all_image_files[file]})")
else:
    print("All files have been processed.")
