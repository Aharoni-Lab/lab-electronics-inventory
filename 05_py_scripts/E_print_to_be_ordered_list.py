from firebase_admin import credentials, storage, initialize_app
import firebase_admin

# Initialize Firebase if not already initialized
cred_path = '/Users/abasaltbahrami/Desktop/aharonilabinventory-firebase-adminsdk-fu6uk-d6f7531b46.json'
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    initialize_app(cred, {
        'storageBucket': 'aharonilabinventory.appspot.com'
    })


def check_and_read_reorder_file():
    """Check if 'to_be_ordered.txt' exists in Firebase Storage and print its content."""
    # Access Firebase Storage bucket
    bucket = storage.bucket()
    blob = bucket.blob('to_be_ordered.txt')

    if blob.exists():
        # Download content as text if file exists
        content = blob.download_as_text()
        print("Contents of 'to_be_ordered.txt':\n")
        print(content)
    else:
        print("File 'to_be_ordered.txt' does not exist in Firebase Storage.")


# Run the function
check_and_read_reorder_file()
