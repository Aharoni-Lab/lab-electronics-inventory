import streamlit as st
from datetime import datetime
import requests
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


if not login():
    st.stop()

# Firebase initialization
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
        cred, {"storageBucket": "aharonilabinventory.appspot.com"})

# Fetch file content from Firebase


def fetch_file_content():
    url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts.txt?alt=media"
    response = requests.get(url)
    return response.text if response.status_code == 200 else f"Failed to fetch file: {response.status_code}"

# Extract structured data


def extract_data(content):
    entries = []
    # Splitting by double newlines assumes blocks are separated properly
    blocks = content.split("\n\n")
    for block in blocks:
        data = {}
        lines = block.split("\n")
        for line in lines:
            parts = line.split(":", 1)  # Split only at the first colon
            if len(parts) == 2:
                key, value = parts[0].strip(), parts[1].strip()
                data[key] = value
        if data:
            entries.append(data)
    return entries

# Display search results


def display_results(entries):
    if not entries:
        st.warning("No data found.")
        return
    df = pd.DataFrame(entries)
    st.write("### Search Results")
    st.table(df)


st.title("Inventory Search & Management")
st.markdown("<h5 style='color: gray;'>Aharoni Lab, CHS 74-134</h5>",
            unsafe_allow_html=True)

if st.button("🔄 Load Inventory Data"):
    file_content = fetch_file_content()
    if file_content.startswith("Failed to fetch file"):
        st.error(file_content)
    else:
        inventory_data = extract_data(file_content)
        display_results(inventory_data)
