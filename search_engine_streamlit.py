import streamlit as st
import requests
import re

# Function to fetch file content from a URL


def fetch_file_content_from_url(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return f"Failed to fetch file: {response.status_code}"

# Function to check if a line is a description


def is_description(line):
    """
    Identifies if a line is likely a component description based on common patterns.
    """
    description_patterns = [
        r'\bDESC\b', r'\bPart Description\b', r'\bCIC\b', r'\bESC\b', r'\bSC\b', r'\bCAP\b',
        r'\bRES\b', r'\bIC\b', r'\bLED\b', r'\bDIODE\b', r'\bMOSFET\b', r'\bREF DES\b',
        r'\bTEST POINT\b', r'\bSCHOTTKY\b', r'\bARRAY\b', r'\bREG LINEAR\b', r'\bPOS ADJ\b',
        r'\bLENS\b', r'\bCHROMA\b', r'\bASPHERE\b', r'\bPRISM\b', r'\bOPTICS\b',
    ]
    description_regex = re.compile(
        '|'.join(description_patterns), re.IGNORECASE)
    return bool(description_regex.search(line))


def search_file(part_number_query, value_query):
    # URLs of files
    urls = {
        'workshop': 'https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts_Workshop.txt?alt=media&token=4c67ff8b-f207-4fec-b585-c007518bb976',
        'federico': 'https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts_Federico.txt?alt=media&token=ee37dbb4-44c8-4a82-8ceb-7c9ce8859688',
        'marcel': 'https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts_Marcel.txt?alt=media&token=0e9da0d2-8f8f-451d-9108-4e2283634894'
    }

    results = []

    def search_in_blocks(blocks, location):
        for block in blocks:
            if not block.strip():
                continue
            part_number_match = re.search(
                r'(?:Lot #|P/N|N):\s*([A-Za-z0-9\-\/# ]+)', block, re.IGNORECASE)
            desc_match = re.search(r'DESC:\s*(.*)', block, re.IGNORECASE)
            if not desc_match:
                block_lines = block.splitlines()
                for i, line in enumerate(block_lines):
                    if is_description(line):
                        desc_match = line.strip()
                        break
            if part_number_match:
                part_number = part_number_match.group(1)
                value = desc_match if desc_match else "Description not available"
                results.append({"part_number": part_number,
                               "value": value, "location": location})

    # Search all files or specific file
    for name, url in urls.items():
        file_content = fetch_file_content_from_url(url)
        if not file_content.startswith("Failed to fetch"):
            blocks = file_content.split("Image:")
            search_in_blocks(blocks, name.capitalize())

    return results


# Streamlit Web App Interface
st.title("Component Search Tool")

part_number_query = st.text_input("Enter part number:")
value_query = st.text_input("Enter component name/value:")

if st.button("Search"):
    results = search_file(part_number_query, value_query)

    if results:
        st.write(f"Search completed. Found {len(results)} items.")
        for result in results:
            st.write(
                f"**Part Number**: {result['part_number']} | **Description**: {result['value']} | **Location**: {result['location']}")
    else:
        st.write("No results found.")
