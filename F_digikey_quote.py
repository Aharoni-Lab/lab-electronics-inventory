import streamlit as st
import requests
import json

# Function to create a DigiKey quote
def create_digikey_quote(auth_token, client_id, customer_id, quote_name):
    url = "https://api.digikey.com/quoting/v4/quotes"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "X-DIGIKEY-Client-Id": client_id,
        "X-DIGIKEY-Customer-Id": customer_id,
        "Content-Type": "application/json"
    }
    data = {
        "QuoteName": quote_name
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response.json()

# Streamlit UI
st.title("DigiKey Quote Generator")

# Input fields for the DigiKey API
auth_token = st.text_input("Enter OAuth Bearer Token", type="password")
client_id = st.text_input("Enter DigiKey Client ID")
customer_id = st.text_input("Enter DigiKey Customer ID")
quote_name = st.text_input("Quote Name")

# Create quote button
if st.button("Create Quote"):
    if auth_token and client_id and customer_id and quote_name:
        response = create_digikey_quote(auth_token, client_id, customer_id, quote_name)
        if response.get("Quote"):
            st.success(f"Quote Created! Quote ID: {response['Quote']['QuoteId']}")
        else:
            st.error("Failed to create quote")
    else:
        st.warning("Please fill in all fields.")
