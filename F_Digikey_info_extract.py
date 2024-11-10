import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
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

    # Try to extract JSON-like data for unit price
    unit_price = "Not found"
    script_tag = soup.find("script", text=re.compile(r'"priceQuantity"'))
    
    if script_tag:
        # Find the JSON-like structure within the script text
        json_text_match = re.search(r'\{.*"priceQuantity":\{.*?\}\}', script_tag.string)
        if json_text_match:
            json_text = json_text_match.group(0)
            try:
                # Load JSON data
                data = json.loads(json_text)
                
                # Access the first unit price in the pricing array
                if "priceQuantity" in data and "pricing" in data["priceQuantity"]:
                    first_price_info = data["priceQuantity"]["pricing"][0]["mergedPricingTiers"][0]
                    unit_price = first_price_info["unitPrice"]
            except json.JSONDecodeError:
                st.error("Failed to parse JSON data from the page.")

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
