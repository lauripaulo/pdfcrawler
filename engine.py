import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple, Any
from PyPDF2 import PdfReader
import csv
import logging
import shutil
import uuid
import xxhash
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)

# Callback constants
CALLBACK_FILE_FOUND = 1
CALLBACK_FILE_VALIDATED = 2
CALLBACK_FILE_COPIED = 3


class CallBack:
    """Progress callback interface with cancellation support."""
    
    def __init__(self) -> None:
        self.cancelled = False
    
    def cancel(self) -> None:
        """Signal that the operation should be cancelled."""
        self.cancelled = True
    
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self.cancelled
    
    def update(self, type: int, message: str) -> None:
        """Called with progress updates.
        
        Args:
            type: Callback type (CALLBACK_FILE_FOUND, CALLBACK_FILE_VALIDATED, CALLBACK_FILE_COPIED)
            message: Progress message
        """
        logging.info(f"Type: {type} - Message: {message}")


@dataclass
class PdfEntry:
    """Represents a PDF file entry with metadata."""
    fullname: str
    size: int
    hash: str
    pages: Optional[int] = None
    info: Optional[Dict[str, str]] = None
    is_duplicate: bool = False
    is_valid: bool = True  # Whether the PDF was validated successfully
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV export."""
        return {
            "title": self.info.get("title", "") if self.info else "",
            "author": self.info.get("author", "") if self.info else "",
            "pages": self.pages or "",
            "size": self.size,
            "size_human": Finder.convert_size(self.size),
            "fullname": self.fullname,
            "is_duplicate": self.is_duplicate,
            "hash": self.hash,
            "is_valid": self.is_valid,
        }
    
    def relative_path(self) -> str:
        """Get the relative path from the parent directory of the file."""
        return str(Path(self.fullname).relative_to(
            Path(self.fullname).parent
        ))


class Finder:
    """Deep module: PDF file discovery, validation, duplicate detection, CSV export, and copy operations.
    
    This module provides a clean interface for PDF file operations. All methods return data
    instead of mutating internal state, making the module testable and thread-safe.
    """
    
    def find_all_pdf_files(
        self, 
        folder: str, 
        callback: Optional[CallBack] = None
    ) -> List[PdfEntry]:
        """Discover PDF files in folder.
        
        Args:
            folder: Path to folder to search
            callback: Optional progress callback with cancellation support
            
        Returns:
            List of PdfEntry objects for each PDF found
        """
        pdf_files: List[PdfEntry] = []
        
        for root, dirs, files in os.walk(folder):
            if callback and callback.is_cancelled():
                break
            
            if callback:
                callback.update(CALLBACK_FILE_FOUND, f"Scanning '{root}'...")
            
            for file in files:
                if callback and callback.is_cancelled():
                    break
                
                if file.endswith(".pdf"):
                    fullname = os.path.join(root, file)
                    entry = PdfEntry(
                        fullname=fullname,
                        size=os.path.getsize(fullname),
                        hash="",  # Will be set during validation
                        pages=None,
                        info=None,
                    )
                    pdf_files.append(entry)
        
        return pdf_files
    
    def validate_pdfs(
        self, 
        pdf_files: List[PdfEntry],
        page_filter: Optional[int] = None,
        size_filter: Optional[int] = None,
        detect_duplicates: bool = False,
        callback: Optional[CallBack] = None
    ) -> List[PdfEntry]:
        """Validate PDFs, extract metadata, apply filters.
        
        Filters work as MINIMUMS: PDFs with fewer pages or smaller size than the
        filter value are excluded.
        
        Args:
            pdf_files: List of PdfEntry objects to validate
            page_filter: Minimum number of pages (None for no filter)
            size_filter: Minimum file size in bytes (None for no filter)
            detect_duplicates: Whether to calculate file hash for duplicate detection
            callback: Optional progress callback with cancellation support
            
        Returns:
            List of validated PdfEntry objects that pass filters
        """
        validated: List[PdfEntry] = []
        
        for entry in pdf_files:
            if callback and callback.is_cancelled():
                logging.info("Validation cancelled by user")
                break
            
            try:
                self._read_pdf_info(entry)
                entry.is_valid = True
                
                # Apply minimum filters: exclude if BELOW the threshold
                if page_filter is not None and entry.pages is not None and entry.pages < page_filter:
                    logging.debug(f"Skipping {entry.fullname}: below page filter ({entry.pages} < {page_filter})")
                    continue
                
                if size_filter is not None and entry.size < size_filter:
                    logging.debug(f"Skipping {entry.fullname}: below size filter ({entry.size} < {size_filter})")
                    continue
                
                # Calculate hash if duplicate detection is enabled
                if detect_duplicates:
                    try:
                        entry.hash = self._calculate_hash(entry.fullname)
                    except Exception as e:
                        logging.warning(f"Error calculating hash for {entry.fullname}: {e}")
                        entry.hash = "N/A"
                
                validated.append(entry)
                
                if callback:
                    callback.update(CALLBACK_FILE_VALIDATED, f"Validated '{entry.fullname}' - Hash: {entry.hash}")
                    
            except Exception as e:
                entry.is_valid = False
                logging.warning(f"Can't open {entry.fullname}: {e}")
                validated.append(entry)
                if callback:
                    callback.update(CALLBACK_FILE_VALIDATED, f"Failed to validate '{entry.fullname}': {e}")
        
        return validated
    
    def detect_duplicates(
        self, 
        pdf_files: List[PdfEntry]
    ) -> List[PdfEntry]:
        """Remove duplicate files based on hash.
        
        Entries with 'N/A' hash are ignored (not considered duplicates).
        The first occurrence of each hash is kept; subsequent duplicates are marked.
        
        Args:
            pdf_files: List of validated PdfEntry objects
            
        Returns:
            List with duplicates marked (is_duplicate=True)
        """
        seen_hashes = set()
        result: List[PdfEntry] = []
        
        for entry in pdf_files:
            # Skip entries with invalid hashes
            if not entry.hash or entry.hash == "N/A":
                result.append(entry)
                continue
            
            if entry.hash in seen_hashes:
                entry.is_duplicate = True
                logging.debug(f"Duplicate found: {entry.fullname} (hash: {entry.hash})")
            else:
                seen_hashes.add(entry.hash)
            
            result.append(entry)
        
        return result
    
    def save_to_csv(
        self, 
        pdf_files: List[PdfEntry], 
        output_path: str
    ) -> None:
        """Export PDF list to CSV file.
        
        Fields: title, author, pages, size (human-readable), fullname, is_duplicate, hash.
        
        Args:
            pdf_files: List of PdfEntry objects to export
            output_path: Path to output CSV file
        """
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            fieldnames = ["title", "author", "pages", "size", "fullname", "is_duplicate", "hash"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for entry in pdf_files:
                d = entry.to_dict()
                writer.writerow({
                    "title": d["title"],
                    "author": d["author"],
                    "pages": d["pages"],
                    "size": d["size_human"],
                    "fullname": d["fullname"],
                    "is_duplicate": d["is_duplicate"],
                    "hash": d["hash"],
                })
            
        logging.info(f"CSV file '{output_path}' saved successfully!")
    
    def copy_files(
        self, 
        pdf_files: List[PdfEntry],
        destination: str,
        overwrite: bool = False,
        rename_with_metadata: bool = False,
        callback: Optional[CallBack] = None
    ) -> List[Tuple[str, str]]:
        """Copy files to destination.
        
        Args:
            pdf_files: List of PdfEntry objects to copy (non-duplicates recommended)
            destination: Destination folder path
            overwrite: Whether to overwrite existing files
            rename_with_metadata: Whether to rename files using title/author metadata
            callback: Optional progress callback with cancellation support
            
        Returns:
            List of (source, destination) tuples for successfully copied files
        """
        copied: List[Tuple[str, str]] = []
        
        for i, entry in enumerate(pdf_files):
            if callback and callback.is_cancelled():
                logging.info("Copy cancelled by user")
                break
            
            # Skip duplicates unless explicitly included
            if entry.is_duplicate:
                logging.debug(f"Skipping duplicate: {entry.fullname}")
                continue
            
            source_file = entry.fullname
            
            # Skip if source file doesn't exist or is empty
            if not os.path.exists(source_file) or os.path.getsize(source_file) == 0:
                logging.warning(f"Skipping empty or inaccessible file: '{source_file}'")
                continue
            
            # Generate destination filename
            if rename_with_metadata and entry.info:
                title = entry.info.get("title", "").strip()
                base = self._sanitize_filename(title) if title else Path(source_file).stem
            else:
                base = Path(source_file).stem
            
            filename = f"{base}.pdf"
            destination_file = os.path.join(destination, filename)
            
            # Handle existing files — only ask for overwrite on conflict
            if os.path.exists(destination_file):
                if not overwrite:
                    filename = f"{base}-{uuid.uuid4()}.pdf"
                    destination_file = os.path.join(destination, filename)
                else:
                    try:
                        os.remove(destination_file)
                    except Exception as e:
                        logging.error(f"Failed to remove existing file '{destination_file}': {e}")
                        continue
            
            try:
                shutil.copyfile(source_file, destination_file)
                copied.append((source_file, destination_file))
                
                if callback:
                    callback.update(CALLBACK_FILE_COPIED, f"Copied '{source_file}' to '{destination_file}'")
                    
            except Exception as e:
                logging.error(f"Failed to copy '{source_file}' to '{destination_file}': {e}")
                if os.path.exists(destination_file):
                    os.remove(destination_file)
                if callback:
                    callback.update(CALLBACK_FILE_COPIED, f"Failed to copy '{source_file}': {e}")
        
        return copied
    
    def _read_pdf_info(self, entry: PdfEntry) -> PdfEntry:
        """Read PDF metadata and update entry in place.
        
        Args:
            entry: PdfEntry to update with metadata
        """
        with open(entry.fullname, "rb") as f:
            pdf = PdfReader(f)
            entry.pages = len(pdf.pages)
            metadata = pdf.metadata
            
            # Extract common metadata fields.
            # PyPDF2's creation_date/modification_date properties parse dates with
            # strptime("D:%Y%m%d%H%M%S%z") which fails on dates without time or timezone
            # (e.g. "D:20240115"). Read raw strings directly to avoid that.
            raw_creation = metadata.get("/CreationDate", "") if metadata else ""
            raw_mod = metadata.get("/ModDate", "") if metadata else ""
            raw_title = metadata.get("/Title", "") if metadata else ""
            raw_author = metadata.get("/Author", "") if metadata else ""
            raw_subject = metadata.get("/Subject", "") if metadata else ""
            raw_creator = metadata.get("/Creator", "") if metadata else ""
            raw_producer = metadata.get("/Producer", "") if metadata else ""

            entry.info = {
                "title": raw_title.strip() if raw_title else "",
                "author": raw_author.strip() if raw_author else "",
                "subject": raw_subject.strip() if raw_subject else "",
                "creator": raw_creator.strip() if raw_creator else "",
                "producer": raw_producer.strip() if raw_producer else "",
                "creation_date": str(raw_creation).strip() if raw_creation else "",
                "mod_date": str(raw_mod).strip() if raw_mod else "",
                "raw": str(dict(metadata)) if metadata else "",
            }
        
        return entry
    
    def _calculate_hash(self, filepath: str) -> str:
        """Calculate xxHash for a file.
        
        Args:
            filepath: Path to file
            
        Returns:
            Hex digest of xxHash
        """
        with open(filepath, "rb") as f:
            hasher = xxhash.xxh64()
            chunk_size = 1024 * 1024  # 1MB chunks
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
            return hasher.hexdigest()
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename by removing invalid characters.
        
        Args:
            filename: The filename to sanitize
            
        Returns:
            A sanitized filename that is safe to use
        """
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
        filename = filename.strip(". ")
        return filename if filename else "untitled"
    
    @staticmethod
    def get_current_folder() -> str:
        """Get the current working folder.
        
        Returns:
            Absolute path to current folder
        """
        return os.path.abspath(os.curdir)
    
    @staticmethod
    def convert_size(size: int) -> str:
        """Convert bytes to human-readable format.
        
        Args:
            size: Size in bytes
            
        Returns:
            Formatted size string (e.g., "1.5 MB")
        """
        kb = size // 1000
        mb = round(kb / 1000, 1)
        if kb > 1000:
            return f"{mb:,.1f} MB"
        else:
            return f"{kb:,d} KB"
