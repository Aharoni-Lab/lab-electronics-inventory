import streamlit as st
import pdfplumber
import re
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO


def extract_quote_data(quote_pdf):
    data = []
    with pdfplumber.open(quote_pdf) as pdf:
        all_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            all_text += text + "\n"

            # Updated regular expression to capture all fields
            matches = re.findall(
                r'PART:\s*([\w\-]+).*?DESC:\s*(.*?)\s+(\d+)\s+\d+\s+1\s+([\d.]+)\s+([\d.]+)',
                text,
                re.DOTALL
            )

            # Parse each match and store it in data
            for match in matches:
                part_number, description, quantity, unit_price, extended_price = match
                data.append({
                    "Part Number": part_number,
                    "Description": description,
                    "Quantity": quantity,
                    "Unit Price": unit_price,
                    "Extended Price": extended_price
                })

    return data, all_text


def fill_order_form(order_form_pdf, data):
    packet = BytesIO()
    can = canvas.Canvas(packet)

    # Static information positions
    can.drawString(430, 750, "17188941")  # PO number
    can.drawString(130, 750, "DigiKey")   # Vendor name
    can.drawString(130, 700, "Abasalt Bahrami")  # Requestor's name
    can.drawString(330, 700, "8729858327")  # Requestor's phone
    can.drawString(130, 650, "441437-AH-86058")  # Project fund

    # Line item positions (start at y = 500 for line items, decrease y for each item)
    y = 500
    for idx, item in enumerate(data[:10]):  # Fill up to 10 items
        can.drawString(50, y, str(idx + 1))  # Item number
        can.drawString(100, y, item["Quantity"])  # Quantity
        can.drawString(150, y, "EA")  # Unit (assuming "EA" for each item)
        can.drawString(200, y, item["Unit Price"])  # Unit price
        can.drawString(300, y, item["Part Number"])  # Catalog/Part number
        can.drawString(400, y, item["Description"])  # Description
        can.drawString(550, y, item["Extended Price"])  # Total/Extended price
        y -= 20  # Move down for the next line item

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
    # Extract data and text from the PDF
    data, extracted_text = extract_quote_data(quote_pdf)

    # Button to display the extracted text
    if st.button("Show Extracted Text"):
        st.text_area("Extracted Text from PDF", extracted_text, height=300)

    # Check if data was successfully extracted
    if len(data) > 0:
        # Display parsed data for debugging
        st.write("Parsed Data from PDF:", data)
        result_pdf = fill_order_form(order_form_pdf, data)
        st.success("Order form filled successfully!")

        # Button to download the filled order form
        st.download_button(
            label="Download Filled Order Form",
            data=result_pdf,
            file_name="Filled_Order_Form.pdf",
            mime="application/pdf"
        )
    else:
        st.error("No data found in the quote. Please check the format.")
