from pdfrw import PdfReader

# Full file path to your PDF
pdf_path = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/Order_Digikey.pdf"


def print_field_names(pdf_path):
    try:
        pdf_reader = PdfReader(pdf_path)
        for page_num, page in enumerate(pdf_reader.pages):
            if page.Annots:
                for annot in page.Annots:
                    if annot.T:
                        field_name = annot.T.strip('()')
                        print(f"Page {page_num + 1} Field Name: {field_name}")
    except Exception as e:
        print(f"Error reading PDF file: {e}")


# Call the function with the correct path
print_field_names(pdf_path)
