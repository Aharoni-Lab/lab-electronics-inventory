import os
import re

# Define the paths to the text files and the main directory
processed_text_file_path = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/04_extracted_info/extracted_texts.txt'
directory_path = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/01_inventory_original_files'

# Function to get processed image filenames from the text file


def get_processed_images(file_path):
    processed_files = set()
    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith("Image: "):
                # Extract the filename after "Image: "
                filename = line.strip().split(": ")[1]
                processed_files.add(filename)
    return processed_files

# Function to get all image files in the directory and its subdirectories with relative paths


def get_all_image_files(directory_path):
    image_extensions = {'.heic', '.jpg',
                        '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
    all_files = {}
    for root, _, files in os.walk(directory_path):
        for file in files:
            if os.path.splitext(file.lower())[1] in image_extensions:
                # Store the relative path to each image file for reference
                relative_path = os.path.relpath(
                    os.path.join(root, file), directory_path)
                all_files[file] = relative_path
    return all_files


# Run the functions and compare sets of image files
all_image_files = get_all_image_files(directory_path)
processed_image_files = get_processed_images(processed_text_file_path)

print("------------------------------------------------")
print(f"Number of images in directory: {len(all_image_files)}")
print(f"Number of images processed: {len(processed_image_files)}")

# Find missing files
missing_files = set(all_image_files.keys()) - processed_image_files
if missing_files:
    print("Some files are missing in the processed text file.")
    print("Missing files:")
    for file in missing_files:
        print(f"{file} (Subfolder: {all_image_files[file]})")
else:
    print("All files have been processed.")
