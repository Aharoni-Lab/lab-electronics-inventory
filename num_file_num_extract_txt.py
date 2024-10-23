import os
import re

# Define the path to the text file and the directory
text_file_path = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/extracted_texts.txt'
directory_path = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/files'

# Function to count IMG_ files in the text file


def count_img_files(file_path):
    img_count = 0

    with open(file_path, 'r') as file:
        lines = file.readlines()

        # Count lines that start with "Image"
        for line in lines:
            if line.strip().startswith('Image'):
                img_count += 1

    return img_count

# Function to count files in the directory


def count_files_in_directory(directory_path):
    try:
        files = os.listdir(directory_path)
        return len(files)
    except FileNotFoundError:
        print(f"Directory not found: {directory_path}")
        return 0


# Count IMG_ files and print the result
img_count = count_img_files(text_file_path)
print(f"Number of IMG_ files: {img_count}")

# Count the number of files in the specified directory
file_count = count_files_in_directory(directory_path)
print(f"Number of files in directory: {file_count}")
