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
    
    # Trying different ways to extract Part Number, Description, and Unit Price
    part_number = soup.find(text="DigiKey Part Number")
    description = soup.find("h1")  # Often, the description is in the <h1> tag
    price = soup.find("span", {"id": "pricing"})

    if part_number:
        part_number_text = part_number.find_next("td").text.strip()
    else:
        part_number_text = "Not found"
    
    description_text = description.text.strip() if description else "Not found"
    
    if price:
        unit_price_text = price.text.strip()
    else:
        # Another way to extract price if the ID-based method fails
        unit_price_text = soup.find("td", {"data-testid": "pricing-table-unit-price"})
        unit_price_text = unit_price_text.text.strip() if unit_price_text else "Not found"

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
    else:
        st.error("Failed to extract data from the page. The page structure may have changed.")
