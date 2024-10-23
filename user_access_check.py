import firebase_admin
from firebase_admin import auth, credentials

# Path to your Firebase service account key JSON file
service_account_path = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/aharonilabinventory-firebase-adminsdk-fu6uk-40d1578c31.json'

# Initialize Firebase SDK
cred = credentials.Certificate(service_account_path)
firebase_admin.initialize_app(cred)

# Example: Sign in user
user = auth.get_user_by_email('abasalt@ucla.edu')
print('Successfully fetched user data:', user.uid)
