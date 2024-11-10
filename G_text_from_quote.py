from pdfrw import PdfReader, PdfWriter, PdfDict
from io import BytesIO
import streamlit as st
import pdfplumber
import re
import pandas as pd
import os


def extract_quote_data(quote_pdf):
    data = []
    with pdfplumber.open(quote_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text()

            # Updated regex pattern for more flexibility
            matches = re.findall(
                r'PART:\s*([\w\-]+)\s*DESC:\s*(.*?)\s+(\d+)\s+\d+\s+\d+\s+([\d.]+)\s+([\d.]+)',
                text,
                re.DOTALL
            )

            # Collecting all matches into a structured format
            for match in matches:
                part_number, description, quantity, unit_price, extended_price = match
                data.append({
                    "Catalog #": part_number.strip(),
                    "Description": description.strip(),
                    "Quantity": quantity,
                    "Unit": "EA",  # Assuming unit is always EA; adjust if needed
                    "Unit Price": unit_price,
                    "Total Price": extended_price
                })
    return data


def fill_pdf(data, template_pdf_path):
    pdf_reader = PdfReader(template_pdf_path)
    pdf_writer = PdfWriter()

    # Track unused text fields to populate with "Total Price" values
    # Adjust range as needed based on available Text fields
    text_fields = [f"Text{i}" for i in range(12, 50)]

    # Fill in form fields on the first page
    for page_num, page in enumerate(pdf_reader.pages):
        if page_num == 0:  # Only fill fields on the first page
            if page.Annots:
                for i, item in enumerate(data[:10]):  # Limiting to 10 items
                    for annot in page.Annots:
                        if annot.T:
                            field_name = annot.T[1:-1]  # Strip parentheses
                            value = None
                            font_size = 10  # Default font size

                            # Fill each field based on the field name
                            if field_name == f"QUAN{i+1}":
                                value = item["Quantity"]
                            elif field_name == f"UNIT{i+1}":
                                value = "1"  # Set Unit to "1" instead of extracted data
                            elif field_name == f"PRICE{i+1}":
                                value = item["Unit Price"]
                            elif field_name == f"CATALOG {i+1}":
                                value = item["Catalog #"]
                            elif field_name == f"DESCRIPTION{i+1}":
                                value = item["Description"]
                                font_size = 8  # Smaller font size for Description

                            if value:
                                annot.update(
                                    PdfDict(V=f"{value}",
                                            AP=PdfDict(N=f"{value}"))
                                )
                                # Update font size for the field, specifically for Description if needed
                                if field_name.startswith("DESCRIPTION"):
                                    annot.update(
                                        PdfDict(
                                            DA=f"/Helvetica {font_size} Tf 0 g")
                                    )

                # Populate "Total Price" values in generic text fields
                for i, item in enumerate(data[:10]):  # Limit to 10 items
                    if i < len(text_fields):
                        field_name = text_fields[i]
                        total_price = item["Total Price"]
                        for annot in page.Annots:
                            if annot.T and annot.T[1:-1] == field_name:
                                annot.update(
                                    PdfDict(V=f"{total_price}", AP=PdfDict(N=f"{total_price}")))
                                break

                # Calculate the overall total and fill it in the "Total" field at the bottom if found
                overall_total = sum(
                    float(item["Total Price"]) for item in data)
                for annot in page.Annots:
                    if annot.T:
                        field_name = annot.T[1:-1]
                        if field_name.lower() == "total":
                            annot.update(PdfDict(V=f"{overall_total:.2f}"))

        pdf_writer.addpage(page)

    # Set NeedAppearances to true after filling the form
    if '/AcroForm' in pdf_reader.Root:
        pdf_reader.Root.AcroForm.update(
            PdfDict(NeedAppearances=PdfDict(NeedAppearances=True)))

    # Write the output to a new PDF
    result_pdf_path = "/tmp/Filled_Order_Form.pdf"
    with open(result_pdf_path, "wb") as f:
        pdf_writer.write(f)
    return result_pdf_path


# Streamlit app layout
st.title("DigiKey Quote to Order Form Filler")
st.write("Upload your DigiKey quote PDF and order form PDF, and let the app automatically fill in the order form.")

quote_pdf = st.file_uploader("Upload DigiKey Quote PDF", type="pdf")
order_form_pdf = st.file_uploader("Upload Order Form PDF Template", type="pdf")

if quote_pdf:
    # Extract data from the uploaded quote
    data = extract_quote_data(quote_pdf)

    # Display extracted data in a table for verification
    if data:
        st.write("Extracted Data from Quote:")
        df = pd.DataFrame(data)
        st.dataframe(df)  # Display the extracted data in a table format
    else:
        st.error("No data found in the quote. Please check the format.")

if quote_pdf and order_form_pdf:
    if len(data) > 0:
        filled_pdf_path = fill_pdf(data, order_form_pdf)
        st.success("Order form filled successfully!")

        # Download button
        with open(filled_pdf_path, "rb") as f:
            st.download_button(
                label="Download Filled Order Form",
                data=f,
                file_name="Filled_Order_Form.pdf",
                mime="application/pdf"
            )

        # Open in default viewer (Safari for PDFs on macOS)
# Open in Safari
        if st.button("Open in Safari"):
            safari_path = "/Applications/Safari.app"
            os.system(f"open -a {safari_path} {filled_pdf_path}")

    else:
        st.error("No data found in the quote. Please check the format.")
