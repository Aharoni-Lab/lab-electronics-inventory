import streamlit as st
from datetime import datetime
import requests
import re
import pandas as pd
import firebase_admin
from firebase_admin import credentials, storage
import time

# Authentication setup using Streamlit secrets


def login():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("Login")
        st.warning(
            "Note: You may need to press the Login button twice due to app state updates.")
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

# Function to upload multiple files (images and PDFs) to Firebase


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
        firebase_admin.initialize_app(
            cred, {'storageBucket': 'aharonilabinventory.appspot.com'})

    # Sidebar for uploading component photos or quotes
    with st.sidebar.expander("📸 Upload Component Photos/Quotes"):
        uploader_name = st.text_input("Your Name")
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
                # Assume each entry is separated by double newlines
                blocks = file_content.split("\n\n")
                search_patterns = []

                if part_number_query:
                    search_patterns.append(re.compile(
                        rf'Part number:\s*{re.escape(part_number_query)}', re.IGNORECASE))
                if value_query:
                    search_patterns.append(re.compile(
                        rf'Description:\s*.*{re.escape(value_query)}.*', re.IGNORECASE))
                if footprint_query:
                    search_patterns.append(re.compile(
                        rf'Location:\s*{re.escape(footprint_query)}', re.IGNORECASE))

                results = []
                for block in blocks:
                    if all(pattern.search(block) for pattern in search_patterns):
                        part_number_match = re.search(
                            r'Part number:\s*(.*)', block, re.IGNORECASE)
                        manufacturer_match = re.search(
                            r'Manufacturer Part number:\s*(.*)', block, re.IGNORECASE)
                        description_match = re.search(
                            r'Description:\s*(.*)', block, re.IGNORECASE)
                        location_match = re.search(
                            r'Location:\s*(.*)', block, re.IGNORECASE)

                        part_number = part_number_match.group(
                            1) if part_number_match else "P/N not detected"
                        manufacturer = manufacturer_match.group(
                            1) if manufacturer_match else "Manufacturer P/N not available"
                        description = description_match.group(
                            1) if description_match else "Description not available"
                        location = location_match.group(
                            1) if location_match else "Location not available"

                        results.append(
                            (part_number, manufacturer, description, location))

                if results:
                    st.write("### Search Results")
                    df_results = pd.DataFrame(results, columns=[
                                              "Part Number", "Manufacturer Part Number", "Description", "Location"])
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
