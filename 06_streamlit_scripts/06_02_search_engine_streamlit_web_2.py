import streamlit as st
from datetime import datetime
import requests
import re
import pandas as pd
import firebase_admin
from firebase_admin import credentials, storage
from PIL import Image
import io
import time
from pdfrw import PdfReader, PdfWriter, PdfDict
import pdfplumber
import os
import threading


# Self-ping function to keep the app awake
def keep_awake():
    while True:
        try:
            url = "https://inventory-aharonilab.streamlit.app"  # Your app URL
            response = requests.get(url)
            if response.status_code == 200:
                print("Self-ping successful!")
            else:
                print(
                    f"Self-ping failed with status code {response.status_code}")
        except Exception as e:
            print(f"Error during self-ping: {e}")
        time.sleep(2 * 60 * 60)  # Wait for 2 hours before the next ping


# Start the self-ping thread
threading.Thread(target=keep_awake, daemon=True).start()


# Authentication setup using Streamlit secrets
def login():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if username == st.secrets["auth"]["username"] and password == st.secrets["auth"]["password"]:
                st.session_state["authenticated"] = True
                st.success("Logged in successfully!")
            else:
                st.error("Invalid username or password")

        return False
    return True


# Function to upload multiple files (images and PDFs) to Firebase in a specific folder


def upload_files(files, uploader_name):
    bucket = storage.bucket()
    for file in files:
        file_name = f"component_images/{uploader_name}/{file.name}"
        blob = bucket.blob(file_name)
        try:
            blob.upload_from_string(file.read(), content_type=file.type)
            st.success(
                f"File '{file.name}' uploaded successfully to folder '{uploader_name}'.")
            time.sleep(2)
        except Exception as e:
            st.error(f"Failed to upload file '{file.name}': {e}")


# Display login screen if not authenticated
if not login():
    st.stop()
else:
    # Firebase initialization using Streamlit secrets
    if not firebase_admin._apps:
        cred = credentials.Certificate({
            "type": st.secrets["firebase"]["type"],
            "project_id": st.secrets["firebase"]["project_id"],
            "private_key_id": st.secrets["firebase"]["private_key_id"],
            "private_key": st.secrets["firebase"]["private_key"].replace("\\n", "\n"),
            "client_email": st.secrets["firebase"]["client_email"],
            "client_id": st.secrets["firebase"]["client_id"],
            "auth_uri": st.secrets["firebase"]["auth_uri"],
            "token_uri": st.secrets["firebase"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
        })
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'aharonilabinventory.appspot.com'
        })

    # Sidebar for uploading component photos or quotes
    with st.sidebar.expander("📸 Upload Component Photos/Quotes"):
        uploader_name = st.text_input("Your Name")  # Uploader's name input
        uploaded_files = st.file_uploader("Choose photos or PDF quotes to upload", type=[
            "jpg", "jpeg", "png", "pdf"], accept_multiple_files=True)
        if uploader_name and uploaded_files and st.button("Upload Files"):
            upload_files(uploaded_files, uploader_name)
        elif not uploader_name:
            st.warning("Please enter your name before uploading.")

    # Function to fetch file content from Firebase Storage

    def fetch_file_content():
        url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts.txt?alt=media"
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            return f"Failed to fetch file: {response.status_code}"

    # Function to check if a line is a description
    def is_description(line):
        description_patterns = [
            r'\bDESC\b', r'\bPart Description\b', r'\bCIC\b', r'\bESC\b',
            r'\bSC\b', r'\bCAP\b', r'\bRES\b', r'\bIC\b', r'\bLED\b',
            r'\bDIODE\b', r'\bMOSFET\b', r'\bREF DES\b', r'\bTEST POINT\b',
            r'\bSCHOTTKY\b', r'\bARRAY\b', r'\bREG LINEAR\b', r'\bPOS ADJ\b',
            r'\bLENS\b', r'\bCHROMA\b', r'\bASPHERE\b', r'\bPRISM\b', r'\bOPTICS\b',
        ]
        description_regex = re.compile(
            '|'.join(description_patterns), re.IGNORECASE)
        return bool(description_regex.search(line))

    # Function to save reorder request to Firebase
    def reorder_item(part_number, description, requester_name):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        re_order_text = f"Date and Time: {current_time}, Part Number: {part_number}, Description: {description}, Requester Name: {requester_name}\n"
        bucket = storage.bucket()
        blob = bucket.blob('to_be_ordered.txt')

        try:
            if blob.exists():
                existing_content = blob.download_as_text()
                re_order_text = existing_content + re_order_text
            blob.upload_from_string(re_order_text)
            st.success("Re-order request saved successfully.")
            time.sleep(2)
        except Exception as e:
            st.error(f"Failed to save re-order request: {e}")

    # Function to upload multiple files to Firebase
    def upload_files(files, uploader_name):
        bucket = storage.bucket()
        for file in files:
            file_name = f"component_images/{uploader_name}/{file.name}"
            blob = bucket.blob(file_name)
            try:
                blob.upload_from_string(file.read(), content_type=file.type)
                st.success(
                    f"File '{file.name}' uploaded successfully to folder '{uploader_name}'.")
                time.sleep(2)
            except Exception as e:
                st.error(f"Failed to upload file '{file.name}': {e}")

    # Main Interface
    st.title("Inventory Search & Management")
    st.markdown("<h5 style='color: gray;'>Aharoni Lab, CHS 74-134</h5>",
                unsafe_allow_html=True)

    with st.container():
        st.header("Search for Components")

        col1, col2, col3 = st.columns(3)
        part_number_query = col1.text_input("Enter Part Number")
        value_query = col2.text_input(
            "Enter Component Name / Value", placeholder="e.g., 4.7uF, 100 OHM, ... XOR")
        footprint_query = col3.text_input("Enter Footprint")

        if st.button("🔎 Search"):
            file_content = fetch_file_content()
            if file_content.startswith("Failed to fetch file"):
                st.error(file_content)
            else:
                blocks = file_content.split("Image:")
                search_patterns = []

                if part_number_query:
                    search_patterns.append(re.compile(
                        rf'{re.escape(part_number_query)}(-ND)?', re.IGNORECASE))
                if value_query:
                    value_query_cleaned = value_query.replace(" ", "")
                    value_query_pattern = "".join([ch + r"\s*" if (i < len(value_query_cleaned) - 1 and ((value_query_cleaned[i].isdigit() and value_query_cleaned[i + 1].isalpha()) or (
                        value_query_cleaned[i].isalpha() and value_query_cleaned[i + 1].isdigit()))) else ch for i, ch in enumerate(value_query_cleaned)])
                    search_patterns.append(re.compile(
                        fr'\b{value_query_pattern}\b', re.IGNORECASE))
                if footprint_query:
                    search_patterns.append(re.compile(
                        rf'\b{re.escape(footprint_query)}\b', re.IGNORECASE))

                results = []
                for block in blocks:
                    if all(pattern.search(block) for pattern in search_patterns):
                        part_number_match = re.search(
                            r'\b[A-Za-z]*\d{3,12}[-/]\d{2,5}[a-zA-Z]?\b', block, re.IGNORECASE)
                        desc_match = re.search(
                            r'DESC:\s*(.*)', block, re.IGNORECASE)
                        if not desc_match:
                            block_lines = block.splitlines()
                            for i, line in enumerate(block_lines):
                                if is_description(line):
                                    desc_match = line.strip()
                                    if "CHROMA" in desc_match.upper() and i + 2 < len(block_lines):
                                        desc_match += " " + \
                                            block_lines[i + 1].strip() + \
                                            " " + block_lines[i + 2].strip()
                                    break
                        location_match = re.search(
                            r'Location:\s*(.*)', block, re.IGNORECASE)
                        part_number = part_number_match.group(
                            0) if part_number_match else "P/N not detected"
                        description = desc_match.group(1) if isinstance(
                            desc_match, re.Match) else desc_match or "Description not available"
                        location = location_match.group(
                            1) if location_match else "Location not available"
                        results.append((part_number, description, location))

                if results:
                    st.write("### Search Results")
                    df_results = pd.DataFrame(
                        results, columns=["Part Number", "Description", "Location"])
                    df_results.index = df_results.index + 1
                    st.table(df_results)
                else:
                    st.warning("No items found matching the search criteria.")

    st.write("### Re-Order Missing Parts")
    with st.expander("Click here to reorder parts", expanded=False):
        with st.form("manual_reorder_form"):
            col1, col2, col3 = st.columns(3)

            part_number = col1.text_input("Part Number for Reorder")
            description = col2.text_input("Description for Reorder")
            requester_name = col3.text_input("Requester Name")

            submit_reorder = st.form_submit_button("Submit Re-Order")

            if submit_reorder:
                if part_number and description and requester_name:
                    reorder_item(part_number, description, requester_name)
                else:
                    st.warning("Please fill in all fields before submitting.")
