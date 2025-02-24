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


def normalize_text(text):
    return re.sub(r'\s+', '', text.strip().lower()) if text else ""


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
        uploaded_files = st.file_uploader("Choose photos or PDF quotes to upload",
                                          type=["jpg", "jpeg", "png", "pdf"],
                                          accept_multiple_files=True)
        if uploader_name and uploaded_files and st.button("Upload Files"):
            upload_files(uploaded_files, uploader_name)
        elif not uploader_name:
            st.warning("Please enter your name before uploading.")

    def fetch_file_content():
        url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts.txt?alt=media"
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            return f"Failed to fetch file: {response.status_code}"

    def reorder_item(manufacturer_pn, description, requester_name):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        re_order_text = (
            f"Date and Time: {current_time}, "
            f"Manufacturer Part Number: {manufacturer_pn}, "
            f"Description: {description}, "
            f"Requester Name: {requester_name}\n"
        )
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

        col1, col2 = st.columns(2)
        part_number_query = col1.text_input("Enter Part Number")
        value_query = col2.text_input(
            "Enter Component Name / Value", placeholder="e.g., 4.7uF, 100 OHM, ... XOR")

        if st.button("🔎 Search"):
            file_content = fetch_file_content()
            if file_content.startswith("Failed to fetch file"):
                st.error(file_content)
            else:
                normalized_part_query = normalize_text(
                    part_number_query) if part_number_query else None
                normalized_value_query = normalize_text(
                    value_query) if value_query else None

                # Split blocks by double newlines
                blocks = file_content.split("\n\n")
                results = []
                for block in blocks:
                    manufacturer_match = re.search(
                        r'Manufacturer Part number:\s*(\S.*)', block, re.IGNORECASE)
                    part_number_match = re.search(
                        r'Part number:\s*(\S.*)', block, re.IGNORECASE)
                    description_match = re.search(
                        r'Description:\s*(\S.*)', block, re.IGNORECASE)
                    location_match = re.search(
                        r'Location:\s*(\S.*)', block, re.IGNORECASE)
                    # For "Fabricated Company" or "Company Made"
                    fabricated_match = re.search(r'(?:Company Made|Fabricated Company):\s*(\S.*)',
                                                 block, re.IGNORECASE)

                    manufacturer_pn = manufacturer_match.group(
                        1).strip() if manufacturer_match else ""
                    part_number = part_number_match.group(
                        1).strip() if part_number_match else ""
                    description = description_match.group(
                        1).strip() if description_match else "Not available"
                    location = location_match.group(
                        1).strip() if location_match else "Not available"
                    company_made = fabricated_match.group(
                        1).strip() if fabricated_match else "Not available"

                    # Decide which part number is final
                    if manufacturer_pn:
                        final_pn = manufacturer_pn
                    elif part_number:
                        final_pn = part_number
                    else:
                        final_pn = "Not available"

                    norm_final_pn = normalize_text(final_pn)
                    norm_description = normalize_text(description)

                    match_part = normalized_part_query in norm_final_pn if normalized_part_query else True
                    match_value = normalized_value_query in norm_description if normalized_value_query else True

                    if match_part and match_value:
                        results.append(
                            (manufacturer_pn, part_number, description, location, company_made))

                if results:
                    st.write("### Search Results")

                    # Open a container with a black border that wraps all results
                    st.markdown(
                        """
                        <div style="border: 2px solid black; padding: 8px; margin: 4px;">
                          <!-- Headers in black, larger font -->
                          <div style="color: black; font-size: 1.2em; display: flex; justify-content: space-between; align-items: center;">
                            <div style="width: 70%;"><strong>Description</strong></div>
                            <div style="width: 25%; text-align: right;"><strong>Location</strong></div>
                          </div>
                          <hr style="margin: 4px 0; padding: 0;">
                        """,
                        unsafe_allow_html=True
                    )

                    # Print each result in blue
                    for m_pn, p_num, desc, loc, comp_made in results:
                        st.markdown(f"""
                            <div style="color: blue; margin: 0; padding: 0;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin: 0; padding: 0;">
                                    <!-- Left side: Description + smaller details -->
                                    <div style="width: 70%;">
                                        <strong>{desc}</strong><br>
                                        <span style="font-size: smaller;">
                                            Manufacturer P/N: {m_pn}<br>
                                            Part Number: {p_num}<br>
                                            Company Made: {comp_made}
                                        </span>
                                    </div>
                                    <!-- Right side: Location -->
                                    <div style="width: 25%; text-align: right;">
                                        {loc}
                                    </div>
                                </div>
                                <hr style="margin: 4px 0; padding: 0;">
                            </div>
                        """, unsafe_allow_html=True)

                    # Close the container div
                    st.markdown("</div>", unsafe_allow_html=True)

                else:
                    st.warning("No items found matching the search criteria.")

    # Reorder Section
    st.write("### Re-Order Missing Parts")
    with st.expander("Click here to reorder parts", expanded=False):
        with st.form("manual_reorder_form"):
            col1, col2, col3 = st.columns(3)
            manufacturer_pn = col1.text_input("Manufacturer P/N")
            description = col2.text_input("Description")
            requester_name = col3.text_input("Requester Name")

            submit_reorder = st.form_submit_button("Submit Re-Order")
            if submit_reorder:
                if manufacturer_pn and description and requester_name:
                    reorder_item(manufacturer_pn, description, requester_name)
                else:
                    st.warning("Please fill in all fields before submitting.")
