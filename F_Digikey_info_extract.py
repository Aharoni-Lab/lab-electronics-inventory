import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

def extract_digikey_info(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        st.error("Failed to retrieve data from DigiKey. Please check the link.")
        return None
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Extract DigiKey Part Number
    part_number = soup.find("td", string="DigiKey Part Number")
    part_number_text = part_number.find_next("td").text.strip() if part_number else "Not found"

    # Extract Manufacturer Product Number
    manufacturer_product_number = soup.find("td", string="Manufacturer Product Number")
    manufacturer_product_number_text = manufacturer_product_number.find_next("td").text.strip() if manufacturer_product_number else "Not found"

    # Extract Description
    description_tag = soup.find("td", string="Description")
    description_text = description_tag.find_next("td").text.strip() if description_tag else "Not found"

    # Extract First Unit Price from Bulk Pricing Table
    unit_price = "Not found"
    price_table = soup.find("table", {"id": "pricing"})
    if price_table:
        # Find all cells that contain a dollar amount using regex, and select the first one
        price_cells = price_table.find_all(text=re.compile(r"\$\d+\.\d{4}"))
        if price_cells:
            unit_price = price_cells[0].strip()  # Get the first unit price available

    return {
        "DigiKey Part Number": part_number_text,
        "Manufacturer Product Number": manufacturer_product_number_text,
        "Description": description_text,
        "Unit Price": unit_price
    }

st.title("DigiKey Electronics Component Information Extractor")
url = st.text_input("Enter DigiKey URL:")

if url:
    data = extract_digikey_info(url)
    if data:
        st.write("### Component Information")
        st.write(f"**DigiKey Part Number:** {data['DigiKey Part Number']}")
        st.write(f"**Manufacturer Product Number:** {data['Manufacturer Product Number']}")
        st.write(f"**Description:** {data['Description']}")
        st.write(f"**Unit Price:** {data['Unit Price']}")
    else:
        st.error("Failed to extract data from the page. The page structure may have changed.")
