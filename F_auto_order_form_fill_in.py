import streamlit as st
import pdfplumber
import re
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO

def extract_quote_data(quote_pdf):
    data = []
    with pdfplumber.open(quote_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            # Regular expression to capture part number, quantity, price etc. Adjust based on actual quote format.
            matches = re.findall(r'Part Number:\s*(\S+)\s*Quantity:\s*(\d+)\s*Price:\s*([\d.]+)', text)
            data.extend(matches)
    return data

def fill_order_form(order_form_pdf, data):
    packet = BytesIO()
    can = canvas.Canvas(packet)
    
    # Adjust positions based on the order form PDF layout
    y = 700  # Starting y position
    for part_number, quantity, price in data:
        can.drawString(100, y, part_number)   # Part number position
        can.drawString(200, y, quantity)      # Quantity position
        can.drawString(300, y, price)         # Price position
        y -= 20  # Move down for the next entry

    can.save()
    packet.seek(0)
    new_pdf = PdfReader(packet)
    
    # Read original order form PDF
    existing_pdf = PdfReader(order_form_pdf)
    output = PdfWriter()

    # Merge new data with original PDF
    page = existing_pdf.pages[0]
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)

    for page_num in range(1, len(existing_pdf.pages)):
        output.add_page(existing_pdf.pages[page_num])

    # Save the final PDF to BytesIO
    result_pdf = BytesIO()
    output.write(result_pdf)
    result_pdf.seek(0)
    return result_pdf

# Streamlit app layout
st.title("DigiKey Quote to Order Form Filler")
st.write("Upload your DigiKey quote and order form, and let the app automatically fill in the order form.")

quote_pdf = st.file_uploader("Upload DigiKey Quote PDF", type="pdf")
order_form_pdf = st.file_uploader("Upload Order Form PDF", type="pdf")

if quote_pdf and order_form_pdf:
    data = extract_quote_data(quote_pdf)
    if data:
        result_pdf = fill_order_form(order_form_pdf, data)
        st.success("Order form filled successfully!")
        st.download_button(
            label="Download Filled Order Form",
            data=result_pdf,
            file_name="Filled_Order_Form.pdf",
            mime="application/pdf"
        )
    else:
        st.error("No data found in the quote. Please check the format.")
