import os
from PyPDF2 import PdfReader
import csv

def find_all_pdf_files(initial_path : str) -> list:
    """
    Find all PDF files in the specified directory and its subdirectories.

    Args:
        initial_path (str): The initial directory path to start the search.

    Returns:
        list: A list of dictionaries containing information about each PDF file found.
              Each dictionary contains the following keys:
              - fullname: The full path of the PDF file.
              - size: The size of the PDF file in bytes.
              - pages: The number of pages in the PDF file.
              - info: Additional information about the PDF file (optional).
    """
    pdf_files = []

    # Percorre a árvore de diretórios
    for root, dirs, files in os.walk(initial_path):
        entry : dict
        for file in files:           
            # Verifica se o arquivo é um PDF
            if file.endswith('.pdf'):
                entry = {
                    "fullname": os.path.join(root, file),
                    "size": os.path.getsize(os.path.join(root, file)),
                    "pages": 0,
                    "info": None
                }
                try:
                    read_pdf_info(entry)
                    pdf_files.append(entry)
                    print(f"Found '{entry['fullname']}'...")
                except Exception as e:
                    print(f"Error reading {entry['fullname']}: {e}")
    return pdf_files


def read_pdf_info(pdf_file : dict):
    with open(pdf_file["fullname"], 'rb') as f:
        pdf = PdfReader(f)
        pdf_file["pages"] = len(pdf.pages)
        pdf_file["info"] = pdf.metadata


if __name__ == "__main__":
    print("Finding pdfs...")
    path = "c:\\"
    pdf_files = find_all_pdf_files(path)
    for entry in pdf_files:
        print(entry)
    with open("pdfs.txt", "w", encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["fullname", "size", "pages", "info"])
        writer.writeheader()
        writer.writerows(pdf_files)
    print("Done!")        
