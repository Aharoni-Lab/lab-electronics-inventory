import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, storage
import time

# Function to fetch file content from Firebase Storage


def fetch_file_content():
    url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts.txt?alt=media"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return f"Failed to fetch file: {response.status_code}"

# Function to extract data fields from text


def extract_data(block):
    part_number_match = re.search(
        r'Part number:\s*(\S+)', block, re.IGNORECASE)
    mf_part_number_match = re.search(
        r'Manufacturer Part number:\s*(\S+)', block, re.IGNORECASE)
    description_match = re.search(r'Description:\s*(.*)', block, re.IGNORECASE)
    location_match = re.search(r'Location:\s*(.*)', block, re.IGNORECASE)

    part_number = part_number_match.group(1) if part_number_match else "N/A"
    mf_part_number = mf_part_number_match.group(
        1) if mf_part_number_match else "N/A"
    description = description_match.group(1) if description_match else "N/A"
    location = location_match.group(1) if location_match else "N/A"

    return part_number, mf_part_number, description, location


# Streamlit UI Setup
st.title("Inventory Search & Management")
st.markdown("<h5 style='color: gray;'>Aharoni Lab, CHS 74-134</h5>",
            unsafe_allow_html=True)

with st.container():
    st.header("Search for Components")

    col1, col2 = st.columns(2)
    part_number_query = col1.text_input("Enter Part Number (P/N)")
    mf_part_number_query = col2.text_input(
        "Enter Manufacturer Part Number (MF P/N)")

    if st.button("🔎 Search"):
        file_content = fetch_file_content()
        if file_content.startswith("Failed to fetch file"):
            st.error(file_content)
        else:
            # Assuming each entry is separated by two newlines
            blocks = file_content.split("\n\n")
            search_results = []

            for block in blocks:
                part_number, mf_part_number, description, location = extract_data(
                    block)
                if (part_number_query and part_number_query.lower() in part_number.lower()) or \
                   (mf_part_number_query and mf_part_number_query.lower() in mf_part_number.lower()):
                    search_results.append(
                        (part_number, mf_part_number, description, location))

            if search_results:
                df_results = pd.DataFrame(search_results, columns=[
                                          "P/N", "MF P/N", "Description", "Location"])
                st.write("### Search Results")
                st.dataframe(df_results)
            else:
                st.warning("No matching components found.")
