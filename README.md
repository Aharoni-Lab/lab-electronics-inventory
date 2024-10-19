# lab-electronics-inventory
This project automates the process of extracting and organizing text from images of electronic components, such as resistors, capacitors, and other small parts commonly found in electronics. The idea is to take pictures of these components and use this tool to extract relevant information from the images and sort the data into an Excel file.


The main steps involved are:

**Image Processing:** The project can handle component photos in different formats, converting them if needed (e.g., from .heic to .jpg).

**Text Extraction:** Using Google's Cloud Vision API, the tool reads the text labels from images, which often contain key information like part numbers, values, and tolerances.

**Data Parsing:** The extracted text is processed to identify important details such as component type (resistor, capacitor), part number, value (e.g., 10K ohm), tolerance (e.g., 5%), and manufacturer (e.g., Murata, Panasonic).

**Data Organization:** The parsed data is sorted and stored in an Excel file for easy access and reference. This organized data includes fields like component type, value, manufacturer, and tolerance, making it easy to keep track of your component inventory.
