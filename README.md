
# Lab Electronics Inventory

This project automates the extraction and organization of text from images of electronic components, such as resistors, capacitors, and other small parts commonly used in electronics. By capturing images of these components, the tool extracts key information and organizes it into an Excel file for easy access and management.

### Key Features:

* **Image Processing:** Supports various image formats, converting them when necessary (e.g., .heic to .jpg).
* **Text Extraction:** Utilizes Google's Cloud Vision API to read labels on components, capturing essential details like part numbers, values, and tolerances.
* **Data Parsing:** Uses OpenAI’s API to process extracted text, identifying component types (resistors, capacitors), part numbers, values (e.g., 10K ohm), tolerances (e.g., 5%), and manufacturers (e.g., Murata, Panasonic).
* **Data Organization:** Stores parsed data in Firebase and provides a user-friendly Streamlit web app for searching components, uploading photos, and reordering missing items.
