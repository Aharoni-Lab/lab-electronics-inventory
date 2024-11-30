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

# Authentication setup using Streamlit secrets


def login():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.sidebar.title("Login")
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")

        if st.sidebar.button("Login"):
            if username == st.secrets["auth"]["username"] and password == st.secrets["auth"]["password"]:
                st.session_state["authenticated"] = True
                st.sidebar.success("Logged in successfully!")
            else:
                st.sidebar.error("Invalid username or password")

    return st.session_state["authenticated"]

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

    # DigiKey Quote to Order Form Filler functions
    def extract_quote_data(quote_pdf):
        data = []
        quote_number = None
        with pdfplumber.open(quote_pdf) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                quote_match = re.search(r'Quote #\s*(\d+)', text)
                if quote_match:
                    quote_number = quote_match.group(0)
                matches = re.findall(
                    r'PART:\s*([\w\-]+)\s*DESC:\s*(.*?)\s+(\d+)\s+\d+\s+\d+\s+([\d.]+)\s+([\d.]+)',
                    text, re.DOTALL
                )
                for match in matches:
                    part_number, description, quantity, unit_price, extended_price = match
                    data.append({
                        "Catalog #": part_number.strip(),
                        "Description": description.strip(),
                        "Quantity": quantity,
                        "Unit Price": unit_price,
                        "Total Price": extended_price
                    })
        return data, quote_number

    def fill_pdf(data, template_pdf_path, quote_number):
        pdf_reader = PdfReader(template_pdf_path)
        pdf_writer = PdfWriter()
        today_date = datetime.today().strftime("%m/%d/%y")
        tax_rate = 0.095

        for page_num, page in enumerate(pdf_reader.pages):
            if page_num == 0:
                if page.Annots:
                    for i, item in enumerate(data[:10]):
                        for annot in page.Annots:
                            if annot.T:
                                field_name = annot.T[1:-1]
                                value = None
                                font_size = 10
                                if field_name == f"QUAN{i+1}":
                                    value = item["Quantity"]
                                elif field_name == f"UNIT{i+1}":
                                    value = "1"
                                elif field_name == f"PRICE{i+1}":
                                    value = item["Unit Price"]
                                elif field_name == f"CATALOG {i+1}":
                                    value = item["Catalog #"]
                                elif field_name == f"DESCRIPTION{i+1}":
                                    value = item["Description"]
                                    font_size = 8
                                elif field_name == f"Text{39 + i}":
                                    value = item["Total Price"]

                                if value:
                                    annot.update(
                                        PdfDict(V=f"{value}", AP=PdfDict(N=f"{value}")))
                                    if field_name.startswith("DESCRIPTION"):
                                        annot.update(
                                            PdfDict(DA=f"/Helvetica {font_size} Tf 0 g"))

                    subtotal = sum(float(item["Total Price"]) for item in data)
                    tax = subtotal * tax_rate
                    total = subtotal + tax

                    for annot in page.Annots:
                        if annot.T:
                            field_name = annot.T[1:-1]
                            if field_name == "Text12":
                                annot.update(
                                    PdfDict(V=today_date, AP=PdfDict(N=today_date)))
                            elif field_name == "Text49":
                                annot.update(
                                    PdfDict(V=f"{subtotal:.2f}", AP=PdfDict(N=f"{subtotal:.2f}")))
                            elif field_name == "Text3":
                                annot.update(
                                    PdfDict(V=f"{tax:.2f}", AP=PdfDict(N=f"{tax:.2f}")))
                            elif field_name == "Text50":
                                annot.update(
                                    PdfDict(V=f"{total:.2f}", AP=PdfDict(N=f"{total:.2f}")))

                    for annot in page.Annots:
                        if annot.T:
                            field_name = annot.T[1:-1]
                            if field_name == "Text1":
                                annot.update(PdfDict(V="", AP=PdfDict(N="")))
                            elif field_name == "Text2":
                                annot.update(PdfDict(V="", AP=PdfDict(
                                    N="Fund Manager Approval Signature Here")))
                            elif field_name == "FAU":
                                annot.update(PdfDict(V="", AP=PdfDict(N="")))
                            elif field_name == "PO#":
                                annot.update(
                                    PdfDict(V=quote_number, AP=PdfDict(N=quote_number)))

        pdf_writer.addpage(page)
        if '/AcroForm' in pdf_reader.Root:
            pdf_reader.Root.AcroForm.update(
                PdfDict(NeedAppearances=PdfDict(NeedAppearances=True)))
        result_pdf_path = "/tmp/Filled_Order_Form.pdf"
        with open(result_pdf_path, "wb") as f:
            pdf_writer.write(f)
        return result_pdf_path

    # Sidebar for DigiKey Quote to Order Form Filler
    with st.sidebar.expander("📄 DigiKey Quote to Order Form Filler"):
        quote_pdf = st.file_uploader("Upload DigiKey Quote PDF", type="pdf")
        order_form_pdf = st.file_uploader(
            "Upload Order Form PDF Template", type="pdf")

        if quote_pdf:
            data, quote_number = extract_quote_data(quote_pdf)
            if not data:
                st.error("No data found in the quote. Please check the format.")

        if quote_pdf and order_form_pdf:
            if len(data) > 0:
                filled_pdf_path = fill_pdf(data, order_form_pdf, quote_number)
                st.success("Order form filled successfully!")
                with open(filled_pdf_path, "rb") as f:
                    st.download_button(
                        label="Download Filled Order Form",
                        data=f,
                        file_name="Filled_Order_Form.pdf",
                        mime="application/pdf"
                    )
                if st.button("Open in Safari"):
                    safari_path = "/Applications/Safari.app"
                    os.system(f"open -a {safari_path} {filled_pdf_path}")

            else:
                st.error("No data found in the quote. Please check the format.")

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

    # Enhanced BOM inventory search function with DNL check
    def search_bom_in_inventory(bom_df, inventory_text):
        inventory_items = inventory_text.split("Image:")
        results = []

        for index, row in bom_df.iterrows():
            value = row.get("Value", "N/A").strip().upper()

            # Skip rows where Value is marked as "DNL" (Do Not Load)
            if value == "DNL":
                continue

            found_location = "X"
            found_description = "X"
            status = "Missing"

            value_pattern = re.compile(
                r'\b' + re.escape(value) + r'\b', re.IGNORECASE)

            for block in inventory_items:
                if value_pattern.search(block):
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

                    found_description = description
                    found_location = location
                    status = "Available"
                    break

            results.append({
                "Value": value,
                "Status": status,
                "Description": found_description,
                "Location": found_location
            })

        result_df = pd.DataFrame(results)

        def highlight_status(val):
            color = 'background-color: green; color: white;' if val == "Available" else 'background-color: red; color: white;'
            return color

        styled_df = result_df.style.applymap(
            highlight_status, subset=['Status'])
        return styled_df

    # Sidebar for BOM upload and inventory check
    with st.sidebar.expander("📋 BOM Inventory Check"):
        bom_file = st.file_uploader(
            "Upload your BOM (CSV format)", type=["csv"])
        check_inventory_button = st.button("Check Inventory")

    # Main section for displaying BOM results
    if bom_file and check_inventory_button:
        bom_df = pd.read_csv(bom_file)
        st.write("Uploaded BOM:")
        st.dataframe(bom_df)

        inventory_text = fetch_file_content()
        bom_results = search_bom_in_inventory(bom_df, inventory_text)

        st.write("### BOM Inventory Check Results")
        st.table(bom_results)

# Function to fetch suggestions for the search query


def get_suggestions(query, inventory_text):
    inventory_items = inventory_text.split("Image:")
    suggestions = set()

    for block in inventory_items:
        # Check if the query matches any value in the block
        if query.lower() in block.lower():
            # Extract component values (e.g., capacitance, resistance, etc.)
            value_match = re.findall(
                r'\b\d+(\.\d+)?[A-Z]*[uUnNpPmMfFkKΩohm]\b', block, re.IGNORECASE)
            if value_match:
                suggestions.update(value_match)
            # Extract descriptions (if no specific value found)
            desc_match = re.findall(r'DESC:\s*(.*)', block, re.IGNORECASE)
            if desc_match:
                suggestions.update(desc_match)

    return sorted(suggestions)[:10]  # Limit to top 10 suggestions


# Main Interface
st.title("Inventory Search & Management")
with st.container():
    st.header("Search for Components")

    # Input fields for search
    col1, col2, col3 = st.columns(3)
    part_number_query = col1.text_input("Enter Part Number")
    value_query = col2.text_input(
        "Enter Component Name / Value", placeholder="e.g., 4.7uF, 100 OHM, ... XOR")
    footprint_query = col3.text_input("Enter Footprint")

    # Suggestion dropdown for component name/value
    if value_query:  # Trigger suggestions when typing in the value field
        inventory_text = fetch_file_content()
        if not inventory_text.startswith("Failed to fetch file"):
            suggestions = get_suggestions(value_query, inventory_text)
            if suggestions:
                selected_suggestion = st.selectbox(
                    "Suggestions:", options=suggestions, index=0)
                st.success(f"You selected: {selected_suggestion}")
            else:
                st.warning("No suggestions found.")

    # Search button functionality
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
