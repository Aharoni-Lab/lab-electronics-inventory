import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def extract_digikey_info(url):
    # Set up headless Chrome for Selenium
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Start the browser
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    time.sleep(5)  # Allow time for the page to fully load

    # Extract DigiKey Part Number
    try:
        part_number = driver.find_element("xpath", "//td[contains(text(),'DigiKey Part Number')]/following-sibling::td").text
    except:
        part_number = "Not found"

    # Extract Manufacturer Product Number
    try:
        manufacturer_product_number = driver.find_element("xpath", "//td[contains(text(),'Manufacturer Product Number')]/following-sibling::td").text
    except:
        manufacturer_product_number = "Not found"

    # Extract Description
    try:
        description = driver.find_element("xpath", "//td[contains(text(),'Description')]/following-sibling::td").text
    except:
        description = "Not found"

    # Extract First Unit Price from Bulk Pricing Table
    try:
        unit_price = driver.find_element("xpath", "//table[@id='pricing']//td[contains(text(),'$')]").text
    except:
        unit_price = "Not found"

    # Close the browser
    driver.quit()

    return {
        "DigiKey Part Number": part_number,
        "Manufacturer Product Number": manufacturer_product_number,
        "Description": description,
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
        st.error("Failed to extract data from the page.")
