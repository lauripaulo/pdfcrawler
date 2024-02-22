import os
from PyPDF2 import PdfReader
import csv
import logging

logging.basicConfig(level=logging.DEBUG)


def find_all_pdf_files(initial_path: str) -> list:
    pdf_files = []
    # Percorre a árvore de diretórios
    for root, dirs, files in os.walk(initial_path):
        entry: dict
        logging.info(f"Searching in '{root}'...")
        for file in files:
            # Verifica se o arquivo é um PDF
            if file.endswith('.pdf'):
                entry = {
                    "fullname": os.path.join(root, file),
                    "size": os.path.getsize(os.path.join(root, file)),
                    "pages": 0,
                    "info": None
                }
                pdf_files.append(entry)
    return pdf_files


def validate_pdfs(pdf_list: list) -> list:
    for entry in pdf_list:
        try:
            read_pdf_info(entry)
        except Exception as e:
            logging.warning(f"Can't open {entry['fullname']}: {e}")
    return pdf_list


def read_pdf_info(pdf_file: dict) -> dict:
    complete_entry: dict = pdf_file
    with open(pdf_file["fullname"], 'rb') as f:
        pdf = PdfReader(f)
        pdf_file["pages"] = len(pdf.pages)
        pdf_file["info"] = pdf.metadata
        complete_entry = pdf_file
        logging.info(
            f"Valid PDF! Num pages: {pdf_file['pages']} path='{pdf_file['fullname']}'...")
    return complete_entry


def save_to_csv(pdf_list: list, filename: str) -> None:
    with open(filename, "w", encoding='utf-8') as f:
        writer = csv.DictWriter(
            f, fieldnames=["fullname", "size", "pages", "info"])
        writer.writeheader()
        writer.writerows(pdf_list)
        logging.info(f"CSV file '{filename}' saved successfully!")


