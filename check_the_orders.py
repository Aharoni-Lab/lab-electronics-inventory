import requests

# URL to the 'to_be_ordered.txt' file in Firebase Storage
file_url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/to_be_ordered.txt?alt=media&token=945490f8-40dd-42ef-b9e0-a1f4b06287b2"


def fetch_and_print_file_content(url):
    response = requests.get(url)

    if response.status_code == 200:
        # If the request is successful, print the file content
        file_content = response.text
        print("Content of to_be_ordered.txt:\n")
        print(file_content)
    else:
        print(f"Failed to fetch file. Status code: {response.status_code}")


# Call the function
fetch_and_print_file_content(file_url)
