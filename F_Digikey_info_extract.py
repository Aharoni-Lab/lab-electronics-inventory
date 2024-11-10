import streamlit as st
import requests
from bs4 import BeautifulSoup


def extract_digikey_info(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        st.error("Failed to retrieve data from DigiKey. Please check the link.")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Extracting information
    part_number = soup.find(
        "td", {"class": "MuiTableCell-root", "data-testid": "product-overview-product-name"})
    description = soup.find(
        "span", {"data-testid": "product-overview-description"})
    price = soup.find("td", {"data-testid": "pricing-table-unit-price"})

    # Check if data is found
    if not part_number or not description or not price:
        st.error(
            "Failed to extract data from the page. The page structure may have changed.")
        return None

    part_number_text = part_number.text.strip()
    description_text = description.text.strip()
    unit_price_text = price.text.strip()

    return {
        "Part Number": part_number_text,
        "Description": description_text,
        "Unit Price": unit_price_text
    }


st.title("DigiKey Electronics Component Information Extractor")
url = st.text_input("Enter DigiKey URL:")

if url:
    data = extract_digikey_info(url)
    if data:
        st.write("### Component Information")
        st.write(f"**Part Number:** {data['Part Number']}")
        st.write(f"**Description:** {data['Description']}")
        st.write(f"**Unit Price:** {data['Unit Price']}")
