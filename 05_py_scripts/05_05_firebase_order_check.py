# -------------------------------------------------------------------------
# Import required modules from firebase_admin and firebase_admin itself.
# -------------------------------------------------------------------------
from firebase_admin import credentials, storage, initialize_app
import firebase_admin

# -------------------------------------------------------------------------
# Set the path to your Firebase Admin SDK JSON file.
# -------------------------------------------------------------------------
cred_path = '/Users/abasaltbahrami/Desktop/json/aharonilabinventory-firebase-adminsdk-fu6uk-d6f7531b46.json'

# -------------------------------------------------------------------------
# Initialize Firebase if it hasn't been initialized already.
# Create a credentials object and initialize the app with the specified storage bucket.
# -------------------------------------------------------------------------
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    initialize_app(cred, {
        'storageBucket': 'aharonilabinventory.appspot.com'
    })

# -------------------------------------------------------------------------
# Check if 'to_be_ordered.txt' exists in Firebase Storage and print its content.
# Additionally, print a message indicating that the file has been read.
# -------------------------------------------------------------------------


def check_and_read_reorder_file():
    """
    Check if 'to_be_ordered.txt' exists in Firebase Storage, print its content,
    and indicate that the file has been read.
    """
    # Access the default Firebase Storage bucket.
    bucket = storage.bucket()
    # Create a blob object representing 'to_be_ordered.txt'.
    blob = bucket.blob('to_be_ordered.txt')

    # Check if the file exists in the bucket.
    if blob.exists():
        # Download the file's content as text.
        content = blob.download_as_text()
        print("Reading file 'to_be_ordered.txt'...\n")
        print("Contents of 'to_be_ordered.txt':\n")
        print(content)
        print("\nFile has been read successfully.")
    else:
        print("File 'to_be_ordered.txt' does not exist in Firebase Storage.")

# -------------------------------------------------------------------------
# Reset 'to_be_ordered.txt' in Firebase Storage to be empty by overwriting it
# with an empty string.
# -------------------------------------------------------------------------


def reset_reorder_file():
    """
    Reset 'to_be_ordered.txt' in Firebase Storage to be empty.
    """
    # Access the default Firebase Storage bucket.
    bucket = storage.bucket()
    # Create a blob object representing 'to_be_ordered.txt'.
    blob = bucket.blob('to_be_ordered.txt')
    # Overwrite the file with an empty string (clearing its contents).
    blob.upload_from_string("", content_type="text/plain")
    print("File 'to_be_ordered.txt' has been reset to empty.")


# -------------------------------------------------------------------------
# Main block: read file content, then prompt the user for the reset operation.
# -------------------------------------------------------------------------
if __name__ == "__main__":
    # First, check and print the file content along with a message indicating it has been read.
    check_and_read_reorder_file()

    # Prompt the user to decide if they want to reset the file.
    user_input = input("\nDo you want to reset 'to_be_ordered.txt'? (Y/N): ")

    # If the user enters 'Y' or 'y', reset the file.
    if user_input.lower() == 'y':
        reset_reorder_file()
        # Optionally, check and print the file content again to confirm the reset.
        print("\nAfter reset:")
        check_and_read_reorder_file()
    else:
        print("File reset aborted.")
