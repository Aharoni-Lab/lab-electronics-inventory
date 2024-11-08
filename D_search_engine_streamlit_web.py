import streamlit as st
from firebase_admin import credentials, initialize_app, storage
import firebase_admin
import requests
import re
from datetime import datetime

# Firebase initialization using Streamlit secrets
if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": st.secrets["type"],
        "project_id": st.secrets["project_id"],
        "private_key_id": st.secrets["private_key_id"],
        # Convert \\n to newlines
        "private_key": st.secrets["private_key"].replace('\\n', '\n'),
        "client_email": st.secrets["client_email"],
        "client_id": st.secrets["client_id"],
        "auth_uri": st.secrets["auth_uri"],
        "token_uri": st.secrets["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["client_x509_cert_url"],
        "universe_domain": st.secrets["universe_domain"]
    })
    initialize_app(cred, {
        'storageBucket': st.secrets["project_id"] + ".appspot.com"
    })

# Function to fetch file content from Firebase Storage


def fetch_file_content():
    try:
        bucket = storage.bucket()
        blob = bucket.blob('extracted_texts.txt')
        return blob.download_as_text() if blob.exists() else "File not found."
    except Exception as e:
        return f"Error fetching file: {e}"

# Function to check if a line is a description


def is_description(line):
    description_patterns = [
        r'\bDESC\b', r'\bPart Description\b', r'\bCIC\b', r'\bESC\b',
        r'\bSC\b', r'\bCAP\b', r'\bRES\b', r'\bIC\b', r'\bLED\b',
        r'\bDIODE\b', r'\bMOSFET\b', r'\bREF DES\b', r'\bTEST POINT\b',
        r'\bSCHOTTKY\b', r'\bARRAY\b', r'\bREG LINEAR\b', r'\bPOS ADJ\b',
        r'\bLENS\b', r'\bCHROMA\b', r'\bASPHERE\b', r'\bPRISM\b', r'\bOPTICS\b',
    ]
    return bool(re.search('|'.join(description_patterns), line, re.IGNORECASE))

# Function to save reorder request to Firebase


def reorder_item(part_number, description, requester_name):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    re_order_text = f"Date and Time: {current_time}, Part Number: {part_number}, Description: {description}, Requester Name: {requester_name}\n"
    try:
        bucket = storage.bucket()
        blob = bucket.blob('to_be_ordered.txt')
        if blob.exists():
            existing_content = blob.download_as_text()
            re_order_text = existing_content + re_order_text
        blob.upload_from_string(re_order_text)
        st.success("Re-order request saved successfully.")
    except Exception as e:
        st.error(f"Failed to save re-order request: {e}")


# Streamlit app layout
st.title("Component Search Tool")

# Search form
part_number_query = st.text_input("Enter part number:")
value_query = st.text_input("Enter component name/value:")
footprint_query = st.text_input("Enter footprint:")

# Search button
if st.button("Search"):
    content = fetch_file_content()
    if content.startswith("Error"):
        st.error(content)
    elif content == "File not found.":
        st.warning(content)
    else:
        # Perform search and display results
        blocks = content.split("Image:")
        results = []
        for block in blocks:
            if not block.strip():
                continue
            if all(re.search(pattern, block, re.IGNORECASE) for pattern in [part_number_query, value_query, footprint_query] if pattern):
                part_number_match = re.search(
                    r'(?:Lot #|P/N|N):\s*([A-Za-z0-9\-\/# ]+)', block, re.IGNORECASE)
                desc_match = re.search(r'DESC:\s*(.*)', block, re.IGNORECASE)
                location_match = re.search(
                    r'Location:\s*(.*)', block, re.IGNORECASE)

                part_number = part_number_match.group(
                    1) if part_number_match else "P/N not detected"
                description = desc_match.group(
                    1) if desc_match else "Description not available"
                location = location_match.group(
                    1) if location_match else "Location not available"

                results.append((part_number, description, location))

        if results:
            st.write("Search Results:")
            for part_number, description, location in results:
                st.write(
                    f"**Part Number:** {part_number}, **Description:** {description}, **Location:** {location}")
        else:
            st.warning("No matches found.")

# Re-order request form
st.header("Re-Order Request")
with st.form("reorder_form"):
    part_number = st.text_input("Part Number")
    description = st.text_input("Description")
    requester_name = st.text_input("Requester Name")
    if st.form_submit_button("Submit Re-Order"):
        reorder_item(part_number, description, requester_name)
