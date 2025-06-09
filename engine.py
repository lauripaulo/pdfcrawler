from operator import call
import os
from PyPDF2 import PdfReader
import csv
import logging
import shutil
import uuid
import hashlib

from pathlib import Path

logging.basicConfig(level=logging.DEBUG)


CALLBACK_FILE_FOUND = 1
CALLBACK_FILE_VALIDATED = 2


class CallBack:
    def update(self, type: int, message: str) -> None:
        logging.info(f"Type: {type} - Message: {message}")


class Finder:
    pdf_files: list = []
    validated_pdf_files: list = []
    file_size_filter: int = 0
    page_size_filter: int = 0

    def find_all_pdf_files(self, initial_path: str, callback: CallBack) -> list:
        # Percorre a árvore de diretórios
        for root, dirs, files in os.walk(initial_path):
            entry: dict
            callback.update(CALLBACK_FILE_FOUND, f"Found folder '{root}'...")
            for file in files:
                # Verifica se o arquivo é um PDF
                if file.endswith(".pdf"):
                    entry = {
                        "fullname": os.path.join(root, file),
                        "size": os.path.getsize(os.path.join(root, file)),
                        "pages": 0,
                        "info": None,
                    }
                    self.pdf_files.append(entry)
        return self.pdf_files

    def validate_pdfs(self, callback: CallBack, detect_duplicates: bool) -> list:
        for entry in self.pdf_files:
            entry["sha256"] = "N/A"
            try:
                self.read_pdf_info(entry)
                if (
                    entry["size"] > self.file_size_filter
                    and entry["pages"] > self.page_size_filter
                ):
                    self.validated_pdf_files.append(entry)
                    # --- Calculate SHA256 if duplicate detection is enabled ---
                    if detect_duplicates:
                        with open(entry["fullname"], "rb") as f:
                            sha256 = hashlib.sha256()
                            while True:
                                chunk = f.read(8192)
                                if not chunk:
                                    break
                                sha256.update(chunk)
                            entry["sha256"] = sha256.hexdigest()
                    # --- End SHA256 ---
            except Exception as e:
                logging.warning(f"Can't open {entry['fullname']}: {e}")
            callback.update(
                CALLBACK_FILE_VALIDATED, f"Validated '{entry['fullname']}' - SHA256: {entry['sha256']}..."
            )
        return self.validated_pdf_files

    def read_pdf_info(self, pdf_file: dict) -> dict:
        complete_entry: dict = pdf_file
        with open(pdf_file["fullname"], "rb") as f:
            pdf = PdfReader(f)
            pdf_file["pages"] = len(pdf.pages)
            metadata = pdf.metadata
            # Extract common metadata fields
            pdf_file["info"] = {
                "title": getattr(metadata, "title", None) or metadata.get("/Title", ""),
                "author": getattr(metadata, "author", None) or metadata.get("/Author", ""),
                "subject": getattr(metadata, "subject", None) or metadata.get("/Subject", ""),
                "creator": getattr(metadata, "creator", None) or metadata.get("/Creator", ""),
                "producer": getattr(metadata, "producer", None) or metadata.get("/Producer", ""),
                "creation_date": getattr(metadata, "creation_date", None) or metadata.get("/CreationDate", ""),
                "mod_date": getattr(metadata, "modification_date", None) or metadata.get("/ModDate", ""),
                "raw": dict(metadata) if metadata else {},
            }
            complete_entry = pdf_file
        return complete_entry

    def save_to_csv(self, filename: str) -> None:
        with open(filename, "w", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["fullname", "size", "pages", "info"], dialect="excel"
            )
            writer.writeheader()
            writer.writerows(self.validated_pdf_files)
            logging.info(f"CSV file '{filename}' saved successfully!")

    def copy_files(self, destination: str, overwrite: bool, callback: CallBack, rename_with_metadata: bool = False) -> None:
        for entry in self.validated_pdf_files:
            filename = ""
            source_file: str = entry["fullname"]
            if rename_with_metadata and entry.get("info"):
                title = entry["info"].get("title", "").strip().replace("/", "_").replace(":", " ")
                base = title if title else Path(entry['fullname']).stem
                filename = f"{base}.pdf"
            else:
                filename = f"{Path(entry['fullname']).stem}.pdf"

            destination_file: str = os.path.join(destination, filename)

            # Validate source file
            if not os.path.exists(source_file) or os.path.getsize(source_file) == 0:
                logging.warning(f"Source file '{source_file}' is inaccessible or empty.")
                continue

            try:
                if os.path.exists(destination_file):
                    if overwrite:
                        try:
                            os.remove(destination_file)
                        except Exception as e:
                            logging.error(f"Error removing file '{destination_file}': {e}")
                            continue
                    else:
                        filename = f"{Path(entry['fullname']).stem}-{uuid.uuid4()}.pdf"
                        destination_file = os.path.join(destination, filename)

                # Perform the copy operation
                shutil.copyfile(source_file, destination_file)
                logging.info(f"File '{source_file}' copied to '{destination_file}'")
                callback.update(
                    CALLBACK_FILE_VALIDATED,
                    f"File '{source_file}' copied to '{destination_file}'",
                )
            except Exception as e:
                logging.error(f"Error copying file '{source_file}' to '{destination_file}': {e}")
                # Remove partially created file
                if os.path.exists(destination_file):
                    os.remove(destination_file)
                callback.update(
                    CALLBACK_FILE_VALIDATED,
                    f"Failed to copy file '{source_file}' to '{destination_file}'",
                )

    @staticmethod
    def get_current_folder() -> str:
        return os.path.abspath(os.curdir)

    @staticmethod
    def convert_size(size):
        """Convert bytes to mb or kb depending on scale"""
        kb = size // 1000
        mb = round(kb / 1000, 1)
        if kb > 1000:
            return f"{mb:,.1f} MB"
        else:
            return f"{kb:,d} KB"
