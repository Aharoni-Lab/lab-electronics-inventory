from pdfrw import PdfReader, PdfWriter, PdfDict
from io import BytesIO
import streamlit as st
import pdfplumber
import re
import pandas as pd


def extract_quote_data(quote_pdf):
    data = []
    with pdfplumber.open(quote_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            matches = re.findall(
                r'PART:\s*([\w\-]+).*?DESC:\s*(.*?)\s+(\d+)\s+\d+\s+1\s+([\d.]+)\s+([\d.]+)',
                text,
                re.DOTALL
            )
            for match in matches:
                part_number, description, quantity, unit_price, extended_price = match
                data.append({
                    "Catalog #": part_number,
                    "Description": description,
                    "Quantity": quantity,
                    "Unit": "EA",  # Assuming unit is always EA; adjust if needed
                    "Unit Price": unit_price,
                    "Total Price": extended_price
                })
    return data


def fill_pdf(data, template_pdf_path):
    pdf_reader = PdfReader(template_pdf_path)
    pdf_writer = PdfWriter()

    for page_num, page in enumerate(pdf_reader.pages):
        if page_num == 0:  # Only fill fields on the first page
            if page.Annots:
                for i, item in enumerate(data[:10]):  # Limiting to 10 items
                    for annot in page.Annots:
                        if annot.T:
                            field_name = annot.T[1:-1]  # Strip parentheses

                            # Debugging print statements
                            print(f"Field Name: {field_name}")
                            if field_name.startswith("QUAN") or field_name.startswith("UNIT") or field_name.startswith("PRICE") or field_name.startswith("CATALOG") or field_name.startswith("DESCRIPTION"):
                                print(
                                    f"Attempting to fill {field_name} with value: {item}")

                            # Fill each field based on the field name
                            if field_name == f"QUAN{i+1}":
                                annot.update(
                                    PdfDict(V='{}'.format(item["Quantity"])))
                            elif field_name == f"UNIT{i+1}":
                                annot.update(
                                    PdfDict(V='{}'.format(item["Unit"])))
                            elif field_name == f"PRICE{i+1}":
                                annot.update(
                                    PdfDict(V='{}'.format(item["Unit Price"])))
                            elif field_name == f"CATALOG {i+1}":
                                annot.update(
                                    PdfDict(V='{}'.format(item["Catalog #"])))
                            elif field_name == f"DESCRIPTION{i+1}":
                                annot.update(
                                    PdfDict(V='{}'.format(item["Description"])))

                # Calculate the overall total and fill it in the "Total" field
                overall_total = sum(
                    float(item["Total Price"]) for item in data)
                for annot in page.Annots:
                    if annot.T:
                        field_name = annot.T[1:-1]
                        if field_name == "Total":
                            annot.update(PdfDict(V=f"{overall_total:.2f}"))

        pdf_writer.addpage(page)

    # Write the output to a new PDF
    result_pdf = BytesIO()
    pdf_writer.write(result_pdf)
    result_pdf.seek(0)
    return result_pdf


# Streamlit app layout
st.title("DigiKey Quote to Order Form Filler")
st.write("Upload your DigiKey quote and order form, and let the app automatically fill in the order form.")

quote_pdf = st.file_uploader("Upload DigiKey Quote PDF", type="pdf")
order_form_pdf = st.file_uploader("Upload Order Form PDF", type="pdf")

if quote_pdf:
    # Extract data from the uploaded quote
    data = extract_quote_data(quote_pdf)

    # Display extracted data in a table for verification
    if data:
        st.write("Extracted Data from Quote:")
        df = pd.DataFrame(data)
        st.dataframe(df)  # Display the extracted data in a table format

if quote_pdf and order_form_pdf:
    if len(data) > 0:
        filled_pdf = fill_pdf(data, order_form_pdf)
        st.success("Order form filled successfully!")

        # Download button
        st.download_button(
            label="Download Filled Order Form",
            data=filled_pdf,
            file_name="Filled_Order_Form.pdf",
            mime="application/pdf"
        )
    else:
        st.error("No data found in the quote. Please check the format.")
