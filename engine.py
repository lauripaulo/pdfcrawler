import os
from PyPDF2 import PdfReader
import csv
import logging

logging.basicConfig(level=logging.DEBUG)


CALLBACK_FILE_FOUND = 1
CALLBACK_FILE_VALIDATED = 2


class CallBack:
    def update(self, type: int, message: str) -> None:
        logging.info(f"Type: {type} - Message: {message}")


class Finder:
    pdf_files: list = []
    validated_pdf_files: list = []

    def find_all_pdf_files(self, initial_path: str, callback: CallBack) -> list:
        # Percorre a árvore de diretórios
        for root, dirs, files in os.walk(initial_path):
            entry: dict
            for file in files:
                # Verifica se o arquivo é um PDF
                if file.endswith('.pdf'):
                    entry = {
                        "fullname": os.path.join(root, file),
                        "size": os.path.getsize(os.path.join(root, file)),
                        "pages": 0,
                        "info": None
                    }
                    self.pdf_files.append(entry)
                    callback.update(CALLBACK_FILE_FOUND, f"Found '{entry}'...")
        return self.pdf_files

    def validate_pdfs(self, callback: CallBack) -> list:
        for entry in self.pdf_files:
            try:
                self.read_pdf_info(entry)
                self.validated_pdf_files.append(entry)
                callback.update(CALLBACK_FILE_VALIDATED,
                                f"Validated '{entry['fullname']}'...")
            except Exception as e:
                logging.warning(f"Can't open {entry['fullname']}: {e}")
        return self.validated_pdf_files

    def read_pdf_info(self, pdf_file: dict) -> dict:
        complete_entry: dict = pdf_file
        with open(pdf_file["fullname"], 'rb') as f:
            pdf = PdfReader(f)
            pdf_file["pages"] = len(pdf.pages)
            pdf_file["info"] = pdf.metadata
            complete_entry = pdf_file
        return complete_entry

    def save_to_csv(self, filename: str) -> None:
        with open(filename, "w", encoding='utf-8') as f:
            writer = csv.DictWriter(
                f, fieldnames=["fullname", "size", "pages", "info"], dialect="excel")
            writer.writeheader()
            writer.writerows(self.validated_pdf_files)
            logging.info(f"CSV file '{filename}' saved successfully!")
