from datetime import datetime
from pdfrw import PdfReader, PdfWriter, PdfDict
from io import BytesIO
import streamlit as st
import pdfplumber
import re
import pandas as pd
import os
import uuid
import glob


def clear_temp_files():
    temp_files = glob.glob("/tmp/Filled_Order_Form_*.pdf")
    for temp_file in temp_files:
        os.remove(temp_file)


def extract_quote_data(quote_pdf):
    data = []
    quote_number = None
    with pdfplumber.open(quote_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text()

            # Extract quote number (e.g., "Quote # 17102424")
            quote_match = re.search(r'Quote #\s*(\d+)', text)
            if quote_match:
                quote_number = quote_match.group(0)

            # Updated regex pattern for parts
            matches = re.findall(
                r'PART:\s*([\w\-]+)\s*DESC:\s*(.*?)\s+(\d+)\s+\d+\s+\d+\s+([\d.]+)\s+([\d.]+)',
                text,
                re.DOTALL
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
    clear_temp_files()  # Clear previous temporary files
    pdf_reader = PdfReader(template_pdf_path)
    pdf_writer = PdfWriter()

    today_date = datetime.today().strftime("%m/%d/%y")
    tax_rate = 0.095  # 9.5% tax

    for page_num, page in enumerate(pdf_reader.pages):
        if page_num == 0:  # Only fill fields on the first page
            if page.Annots:
                for i, item in enumerate(data[:10]):
                    for annot in page.Annots:
                        if annot.T:
                            field_name = annot.T[1:-1]
                            value = None
                            font_size = 10

                            # Map data to specific fields
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
                                    PdfDict(V=f"{value}",
                                            AP=PdfDict(N=f"{value}"))
                                )
                                if field_name.startswith("DESCRIPTION"):
                                    annot.update(
                                        PdfDict(
                                            DA=f"/Helvetica {font_size} Tf 0 g")
                                    )

                # Calculate subtotal, tax, and total
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

    # Generate a unique path for the output file to avoid caching issues
    result_pdf_path = f"/tmp/Filled_Order_Form_{uuid.uuid4()}.pdf"
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
    data, quote_number = extract_quote_data(quote_pdf)

    # Display extracted data in a table for verification
    if data:
        st.write("Extracted Data from Quote:")
        df = pd.DataFrame(data)
        st.dataframe(df)  # Display the extracted data in a table format
    else:
        st.error("No data found in the quote. Please check the format.")

if quote_pdf and order_form_pdf:
    if len(data) > 0:
        filled_pdf_path = fill_pdf(data, order_form_pdf, quote_number)
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
        if st.button("Open in Safari"):
            safari_path = "/Applications/Safari.app"
            os.system(f"open -a {safari_path} {filled_pdf_path}")
    else:
        st.error("No data found in the quote. Please check the format.")
