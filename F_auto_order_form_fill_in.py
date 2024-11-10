import streamlit as st
import pdfplumber
import re
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO


def extract_quote_data(quote_pdf):
    data = []
    all_text = ""
    with pdfplumber.open(quote_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            all_text += text + "\n"
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
                    "Unit": "EA",
                    "Unit Price": unit_price
                })
    return data, all_text


def create_overlay(data):
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica", 8)

    # Starting y-coordinate for the first row in the lower table
    y_start = 270  # Adjusted to target the lower table
    x_positions = {
        "Quantity": 100,       # x-position for Quantity
        "Unit": 150,          # x-position for Unit
        "Unit Price": 220,    # x-position for Unit Price
        "Catalog #": 310,     # x-position for Catalog #
        "Description": 450    # x-position for Description
    }

    y = y_start
    # Limiting to 10 rows to fit in the table
    for idx, item in enumerate(data[:10]):
        can.drawString(x_positions["Quantity"], y, item["Quantity"])
        can.drawString(x_positions["Unit"], y, item["Unit"])
        can.drawString(x_positions["Unit Price"], y, item["Unit Price"])
        can.drawString(x_positions["Catalog #"], y, item["Catalog #"])
        can.drawString(x_positions["Description"], y, item["Description"])
        y -= 20  # Move down for the next row

    can.save()
    packet.seek(0)
    return PdfReader(packet)


def merge_pdfs(order_form_pdf, overlay_pdf):
    order_form = PdfReader(order_form_pdf)
    output_pdf = PdfWriter()

    for page_num in range(len(order_form.pages)):
        page = order_form.pages[page_num]
        if page_num == 0:
            page.merge_page(overlay_pdf.pages[0])
        output_pdf.add_page(page)

    result_pdf = BytesIO()
    output_pdf.write(result_pdf)
    result_pdf.seek(0)
    return result_pdf


# Streamlit app layout
st.title("DigiKey Quote to Order Form Filler")
st.write("Upload your DigiKey quote and order form, and let the app automatically fill in the order form.")

quote_pdf = st.file_uploader("Upload DigiKey Quote PDF", type="pdf")
order_form_pdf = st.file_uploader("Upload Order Form PDF", type="pdf")

if quote_pdf and order_form_pdf:
    data, extracted_text = extract_quote_data(quote_pdf)

    if st.button("Show Extracted Text"):
        st.text_area("Extracted Text from PDF", extracted_text, height=300)

    if len(data) > 0:
        overlay_pdf = create_overlay(data)
        filled_pdf = merge_pdfs(order_form_pdf, overlay_pdf)
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
