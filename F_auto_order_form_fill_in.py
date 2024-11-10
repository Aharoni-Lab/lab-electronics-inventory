from pdfrw import PdfReader, PdfWriter, PdfDict
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PyPDF2 import PdfMerger
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


def create_overlay(data):
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica", 8)

    y_start = 450  # Adjust based on the vertical position of the first row in the table
    x_positions = {
        "Quantity": 70,
        "Unit": 120,
        "Unit Price": 170,
        "Catalog #": 250,
        "Description": 350,
        "Total": 500
    }

    y = y_start
    for i, item in enumerate(data[:10]):
        can.drawString(x_positions["Quantity"], y, item["Quantity"])
        can.drawString(x_positions["Unit"], y, item["Unit"])
        can.drawString(x_positions["Unit Price"], y, item["Unit Price"])
        can.drawString(x_positions["Catalog #"], y, item["Catalog #"])
        can.drawString(x_positions["Description"], y, item["Description"])
        y -= 20  # Move down for the next line

    overall_total = sum(float(item["Total Price"]) for item in data)
    can.drawString(x_positions["Total"], y - 20, f"{overall_total:.2f}")

    can.save()
    packet.seek(0)
    return packet


def merge_pdfs(order_form_pdf, overlay_pdf):
    merger = PdfMerger()
    order_form = PdfReader(order_form_pdf)
    overlay = PdfReader(overlay_pdf)

    output_pdf = PdfWriter()
    for page_num in range(len(order_form.pages)):
        page = order_form.pages[page_num]
        if page_num == 0:  # Only overlay the first page
            page.merge_page(overlay.pages[0])
        output_pdf.add_page(page)

    result_pdf = BytesIO()
    output_pdf.write(result_pdf)
    result_pdf.seek(0)
    return result_pdf


# Streamlit app layout
st.title("DigiKey Quote to Order Form Filler (Flattened)")
st.write("Upload your DigiKey quote and order form, and let the app automatically fill in and flatten the order form.")

quote_pdf = st.file_uploader("Upload DigiKey Quote PDF", type="pdf")
order_form_pdf = st.file_uploader("Upload Order Form PDF", type="pdf")

if quote_pdf:
    data = extract_quote_data(quote_pdf)

    if data:
        st.write("Extracted Data from Quote:")
        df = pd.DataFrame(data)
        st.dataframe(df)

if quote_pdf and order_form_pdf:
    if len(data) > 0:
        overlay_pdf = create_overlay(data)
        filled_pdf = merge_pdfs(order_form_pdf, overlay_pdf)
        st.success("Order form filled and flattened successfully!")

        st.download_button(
            label="Download Filled Order Form",
            data=filled_pdf,
            file_name="Filled_Order_Form_Flattened.pdf",
            mime="application/pdf"
        )
    else:
        st.error("No data found in the quote. Please check the format.")
