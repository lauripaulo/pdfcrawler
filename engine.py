from operator import call
import os
from PyPDF2 import PdfReader
import csv
import logging
import shutil
import uuid
import xxhash

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
            entry["hash"] = "N/A"
            try:
                self.read_pdf_info(entry)
                if (
                    entry["size"] > self.file_size_filter
                    and entry["pages"] > self.page_size_filter
                ):
                    self.validated_pdf_files.append(entry)
                    # --- Calculate xxHash if duplicate detection is enabled ---
                    if detect_duplicates:
                        try:
                            with open(entry["fullname"], "rb") as f:
                                hasher = xxhash.xxh64()
                                # Use larger chunks for better performance
                                chunk_size = 1024 * 1024  # 1MB chunks
                                while True:
                                    chunk = f.read(chunk_size)
                                    if not chunk:
                                        break
                                    hasher.update(chunk)
                                entry["hash"] = hasher.hexdigest()
                        except Exception as e:
                            logging.warning(
                                f"Error calculating hash for {entry['fullname']}: {e}"
                            )
                            entry["hash"] = "ERROR"
                    # --- End xxHash ---
            except Exception as e:
                logging.warning(f"Can't open {entry['fullname']}: {e}")
            callback.update(
                CALLBACK_FILE_VALIDATED,
                f"Validated '{entry['fullname']}' - Hash: {entry['hash']}...",
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
                "author": getattr(metadata, "author", None)
                or metadata.get("/Author", ""),
                "subject": getattr(metadata, "subject", None)
                or metadata.get("/Subject", ""),
                "creator": getattr(metadata, "creator", None)
                or metadata.get("/Creator", ""),
                "producer": getattr(metadata, "producer", None)
                or metadata.get("/Producer", ""),
                "creation_date": getattr(metadata, "creation_date", None)
                or metadata.get("/CreationDate", ""),
                "mod_date": getattr(metadata, "modification_date", None)
                or metadata.get("/ModDate", ""),
                "raw": dict(metadata) if metadata else {},
            }
            complete_entry = pdf_file
        return complete_entry

    def save_to_csv(self, filename: str) -> None:
        with open(filename, "w", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["fullname", "size", "pages", "info", "hash"],
                dialect="excel",
            )
            writer.writeheader()
            writer.writerows(self.validated_pdf_files)
            logging.info(f"CSV file '{filename}' saved successfully!")

    def copy_files(
        self,
        destination: str,
        overwrite: bool,
        callback: CallBack,
        rename_with_metadata: bool = False,
    ) -> None:
        for entry in self.validated_pdf_files:
            source_file = entry["fullname"]

            # Skip if source file doesn't exist or is empty
            if not os.path.exists(source_file) or os.path.getsize(source_file) == 0:
                logging.warning(f"Skipping empty or inaccessible file: '{source_file}'")
                continue

            # Generate destination filename
            if rename_with_metadata and entry.get("info"):
                title = entry["info"].get("title", "").strip()
                base = (
                    self._sanitize_filename(title) if title else Path(source_file).stem
                )
            else:
                base = Path(source_file).stem

            filename = f"{base}.pdf"
            destination_file = os.path.join(destination, filename)

            # Handle existing files
            if os.path.exists(destination_file):
                if not overwrite:
                    filename = f"{base}-{uuid.uuid4()}.pdf"
                    destination_file = os.path.join(destination, filename)
                else:
                    try:
                        os.remove(destination_file)
                    except Exception as e:
                        logging.error(
                            f"Failed to remove existing file '{destination_file}': {e}"
                        )
                        continue

            try:
                shutil.copyfile(source_file, destination_file)
                callback.update(
                    CALLBACK_FILE_VALIDATED,
                    f"Copied '{source_file}' to '{destination_file}'",
                )
            except Exception as e:
                logging.error(
                    f"Failed to copy '{source_file}' to '{destination_file}': {e}"
                )
                if os.path.exists(destination_file):
                    os.remove(destination_file)
                callback.update(
                    CALLBACK_FILE_VALIDATED, f"Failed to copy '{source_file}'"
                )

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename by removing invalid characters and ensuring it's not empty.

        Args:
            filename: The filename to sanitize

        Returns:
            A sanitized filename that is safe to use
        """
        # Remove invalid characters and ensure the filename is not empty
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
        # Remove leading/trailing spaces and dots
        filename = filename.strip(". ")
        # If filename is empty after sanitization, use a default name
        return filename if filename else "untitled"

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
