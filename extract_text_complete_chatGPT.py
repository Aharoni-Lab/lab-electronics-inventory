import openai
import os
from google.cloud import vision
import io
import logging
import openai


# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Set Google Cloud Vision API credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/aharonilab-9410614763f1.json"

# Initialize Google Cloud Vision API client
client = vision.ImageAnnotatorClient()

# Set up OpenAI API key
openai.api_key = "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"  # Replace with your actual API key

# Function to extract text from image using Google Cloud Vision API


def extract_text_from_image(image_path):
    try:
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
    except Exception as e:
        logging.error(f"Error extracting text from image: {str(e)}")
        return None

# Function to send extracted text to ChatGPT for field extraction


def extract_key_fields_with_chatgpt(extracted_text):
    prompt = f"Extract the following details from the text: Part Number, Mfg Part Number, Description, Type, Value, Tolerance, Quantity, Footprint, Vendor, Country of Origin, Lead Free Status.\n\nText: {extracted_text}"

    try:
        response = openai.Completion.create(
            engine="gpt-3.5-turbo",  # Using GPT-3.5-turbo
            prompt=prompt,
            max_tokens=50,
            temperature=0.2  # Lower temperature for more consistent outputs
        )
        return response.choices[0].text.strip()
    except Exception as e:
        logging.error(f"Error in extracting fields with ChatGPT: {str(e)}")
        return None


# Function to process the image through both Google Vision and ChatGPT APIs


def process_image(image_path):
    # Step 1: Extract text using Google Cloud Vision
    extracted_text = extract_text_from_image(image_path)
    if not extracted_text:
        logging.error("No text detected from image.")
        return None

    logging.info(f"Extracted Text from {image_path}: {extracted_text}")

    # Step 2: Send the extracted text to ChatGPT for structured data extraction
    structured_data = extract_key_fields_with_chatgpt(extracted_text)
    if not structured_data:
        logging.error(
            f"ChatGPT could not extract the fields from {image_path}.")
        return None

    logging.info(f"Structured Data for {image_path}: {structured_data}")

    return structured_data

# Process all images in a directory


def process_all_images_in_directory(directory):
    results = []

    for filename in os.listdir(directory):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(directory, filename)
            logging.info(f"Processing {filename}...")

            # Process each image and append the result
            result = process_image(image_path)
            if result:
                results.append({"Image": filename, "Extracted Data": result})

    return results


# Example usage
if __name__ == "__main__":
    image_directory = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/converted_to_jpeg"

    # Process all images in the directory and get structured data
    structured_data_list = process_all_images_in_directory(image_directory)

    # Print out the results
    for data in structured_data_list:
        print(f"Image: {data['Image']}")
        print(f"Extracted Data:\n{data['Extracted Data']}\n")
