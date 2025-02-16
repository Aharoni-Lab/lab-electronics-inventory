import streamlit as st
import openai
import requests
import re
import pandas as pd
import firebase_admin
from firebase_admin import credentials, storage
from datetime import datetime
import pdfplumber
import time

# Load API keys securely
openai.api_key = st.secrets["openai"]["api_key"]

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
        cred, {'storageBucket': 'aharonilabinventory.appspot.com'})

# Authentication function


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


if not login():
    st.stop()

# Upload files to Firebase Storage


def upload_files(files, uploader_name):
    bucket = storage.bucket()
    for file in files:
        blob = bucket.blob(f"component_images/{uploader_name}/{file.name}")
        try:
            blob.upload_from_string(file.read(), content_type=file.type)
            st.success(f"File '{file.name}' uploaded successfully!")
        except Exception as e:
            st.error(f"Failed to upload '{file.name}': {e}")

# AI-powered search


def ai_search(query):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You help users find electronic components based on descriptions."},
            {"role": "user", "content": f"Find the best matching component for: {query}"}
        ]
    )
    return response["choices"][0]["message"]["content"]

# Fetch text file from Firebase Storage


def fetch_file_content():
    url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts.txt?alt=media"
    response = requests.get(url)
    return response.text if response.status_code == 200 else None


# Main UI
st.title("Inventory Search & Management")
st.markdown("<h5 style='color: gray;'>Aharoni Lab, CHS 74-134</h5>",
            unsafe_allow_html=True)

with st.sidebar.expander("📸 Upload Component Photos/Quotes"):
    uploader_name = st.text_input("Your Name")
    uploaded_files = st.file_uploader("Choose files to upload", type=[
                                      "jpg", "jpeg", "png", "pdf"], accept_multiple_files=True)
    if uploader_name and uploaded_files and st.button("Upload Files"):
        upload_files(uploaded_files, uploader_name)

st.header("Search for Components")
query = st.text_input("Describe the component you need")
if st.button("🔎 AI Search"):
    if query:
        ai_response = ai_search(query)
        st.write("### AI Suggested Component")
        st.write(ai_response)
    else:
        st.warning("Please enter a query before searching.")

st.write("### Re-Order Missing Parts")
with st.expander("Click here to reorder parts"):
    with st.form("manual_reorder_form"):
        col1, col2, col3 = st.columns(3)
        part_number = col1.text_input("Part Number")
        description = col2.text_input("Description")
        requester_name = col3.text_input("Requester Name")
        submit_reorder = st.form_submit_button("Submit Re-Order")

        if submit_reorder:
            if part_number and description and requester_name:
                reorder_text = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, {part_number}, {description}, {requester_name}\n"
                bucket = storage.bucket()
                blob = bucket.blob('to_be_ordered.txt')
                try:
                    existing_content = blob.download_as_text() if blob.exists() else ""
                    blob.upload_from_string(existing_content + reorder_text)
                    st.success("Re-order request saved successfully.")
                except Exception as e:
                    st.error(f"Failed to save request: {e}")
            else:
                st.warning("Please fill in all fields before submitting.")
