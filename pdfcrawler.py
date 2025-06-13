from ast import Call
from gc import callbacks
import os
import logging
import threading
from pathlib import Path
from tkinter import X, Y, BOTH, DISABLED, END, E, W, YES, LEFT, RIGHT, TOP, BOTTOM
from tkinter import filedialog, messagebox

import ttkbootstrap as tkb
from ttkbootstrap.constants import PRIMARY, SUCCESS, INDETERMINATE, NORMAL, INFO
from ttkbootstrap.tableview import Tableview
from ttkbootstrap.scrolled import ScrolledFrame

from engine import CALLBACK_FILE_FOUND, CALLBACK_FILE_VALIDATED, CallBack, Finder


class PDFCrawler(tkb.Window):
    page_size_translate: dict = {"All": 0, ">5": 5, ">10": 10, ">20": 20}
    pdf_size_translate: dict = {
        "All": 0,
        ">1MB": 1 * 1024 * 1024,
        ">5MB": 5 * 1024 * 1024,
        ">10MB": 10 * 1024 * 1024,
    }

    def __init__(self, root: tkb.Window):
        root.geometry("1280x800")  # Increased window size
        root.minsize(1024, 700)    # Set minimum size
        root.title("PDF Crawler - Find and Organize Your PDFs")

        self.page_size_options = ["All", ">5", ">10", ">20"]
        self.pdf_size_options = ["All", ">1MB", ">5MB", ">10MB"]
        self.finder = Finder()
        self.root = root  # Store root window reference

        # Create main container with padding
        self.main_container = tkb.Frame(root, padding=10)
        self.main_container.pack(fill=BOTH, expand=YES)

        # Create top section for controls
        self.create_control_section()
        
        # Create middle section for progress
        self.create_progress_section()
        
        # Create bottom section for results
        self.create_results_section()

    def create_control_section(self):
        """Create the top control section with folder selection and filters"""
        control_frame = tkb.LabelFrame(
            self.main_container,
            text="Search Controls",
            padding=10,
            bootstyle=INFO
        )
        control_frame.pack(fill=X, pady=(0, 10))

        # Folder selection row
        folder_frame = tkb.Frame(control_frame)
        folder_frame.pack(fill=X, pady=(0, 10))
        
        self.lbl_folder = tkb.Label(folder_frame, text="Search Folder:", width=12)
        self.lbl_folder.pack(side=LEFT, padx=(0, 5))
        
        self.etr_folder = tkb.Entry(folder_frame)
        self.etr_folder.insert(0, self.finder.get_current_folder())
        self.etr_folder.pack(side=LEFT, fill=X, expand=YES, padx=(0, 5))
        
        self.btn_pick_folder = tkb.Button(
            folder_frame,
            text="Browse...",
            bootstyle="primary-outline",
            command=self.on_btn_pick_folder_click,
            width=10
        )
        self.btn_pick_folder.pack(side=LEFT)

        # Filters row
        filters_frame = tkb.Frame(control_frame)
        filters_frame.pack(fill=X)
        
        # Page size filter
        page_frame = tkb.Frame(filters_frame)
        page_frame.pack(side=LEFT, padx=(0, 20))
        self.lbl_pages = tkb.Label(page_frame, text="Min Pages:", width=10)
        self.lbl_pages.pack(side=LEFT, padx=(0, 5))
        self.cmb_page_size = tkb.Combobox(
            page_frame,
            values=self.page_size_options,
            width=8,
            state="readonly"
        )
        self.cmb_page_size.current(0)
        self.cmb_page_size.pack(side=LEFT)

        # File size filter
        size_frame = tkb.Frame(filters_frame)
        size_frame.pack(side=LEFT, padx=(0, 20))
        self.lbl_pdf_size = tkb.Label(size_frame, text="Min Size:", width=10)
        self.lbl_pdf_size.pack(side=LEFT, padx=(0, 5))
        self.cmb_pdf_size = tkb.Combobox(
            size_frame,
            values=self.pdf_size_options,
            width=8,
            state="readonly"
        )
        self.cmb_pdf_size.current(0)
        self.cmb_pdf_size.pack(side=LEFT)

        # Duplicate detection
        dup_frame = tkb.Frame(filters_frame)
        dup_frame.pack(side=LEFT, padx=(0, 20))
        self.lbl_detect_duplicates = tkb.Label(dup_frame, text="Detect Duplicates:", width=14)
        self.lbl_detect_duplicates.pack(side=LEFT, padx=(0, 5))
        self.cmb_detect_duplicates = tkb.Combobox(
            dup_frame,
            values=["NO", "YES"],
            width=5,
            state="readonly"
        )
        self.cmb_detect_duplicates.current(0)
        self.cmb_detect_duplicates.pack(side=LEFT)

        # Search button
        self.btn_find = tkb.Button(
            filters_frame,
            text="Start Search",
            bootstyle="success",
            command=self.on_btn_find_click,
            width=15
        )
        self.btn_find.pack(side=RIGHT)

    def create_progress_section(self):
        """Create the progress section with progress bar and status"""
        progress_frame = tkb.LabelFrame(
            self.main_container,
            text="Progress",
            padding=10,
            bootstyle=INFO
        )
        progress_frame.pack(fill=X, pady=(0, 10))

        self.progressbar = tkb.Progressbar(
            master=progress_frame,
            mode=INDETERMINATE,
            bootstyle=(SUCCESS, "striped")
        )
        self.progressbar.pack(fill=X, pady=(0, 5))
        
        self.lbl_progress = tkb.Label(
            progress_frame,
            text="Ready to start...",
            wraplength=1200
        )
        self.lbl_progress.pack(fill=X)

    def create_results_section(self):
        """Create the results section with table and action buttons"""
        results_frame = tkb.LabelFrame(
            self.main_container,
            text="Results",
            padding=10,
            bootstyle=INFO
        )
        results_frame.pack(fill=BOTH, expand=YES)

        # Create table with scrollable frame
        table_frame = ScrolledFrame(results_frame)
        table_frame.pack(fill=BOTH, expand=YES, pady=(0, 10))

        # Configure table columns
        headings = [
            {"text": "Size", "width": 100, "anchor": "w"},
            {"text": "Pages", "width": 80, "anchor": "w"},
            {"text": "File", "width": 300, "anchor": "w"},
            {"text": "Full Path", "width": 700, "anchor": "w"},
        ]

        self.tableview = Tableview(
            master=table_frame,
            coldata=headings,
            searchable=True,
            bootstyle=PRIMARY,
            paginated=True,
            pagesize=25,
            stripecolor=(self.root.style.colors.light, self.root.style.colors.dark),
        )
        self.tableview.pack(fill=BOTH, expand=YES)

        # Action buttons
        actions_frame = tkb.Frame(results_frame)
        actions_frame.pack(fill=X)

        # Left side - Export options
        export_frame = tkb.Frame(actions_frame)
        export_frame.pack(side=LEFT)
        
        self.btn_export_csv = tkb.Button(
            export_frame,
            text="Export to CSV",
            bootstyle="primary-outline",
            command=self.on_btn_export_csv_click,
            state=DISABLED,
            width=15
        )
        self.btn_export_csv.pack(side=LEFT, padx=(0, 10))

        # Right side - Copy options
        copy_frame = tkb.Frame(actions_frame)
        copy_frame.pack(side=RIGHT)
        
        self.rename_var = tkb.BooleanVar(value=False)
        self.chk_rename = tkb.Checkbutton(
            copy_frame,
            text="Rename with Title & Author",
            variable=self.rename_var,
            bootstyle="info-toolbutton",
            width=25
        )
        self.chk_rename.pack(side=LEFT, padx=(0, 10))
        
        self.btn_copy = tkb.Button(
            copy_frame,
            text="Copy Files To...",
            bootstyle="success-outline",
            command=self.on_btn_copy_click,
            state=DISABLED,
            width=15
        )
        self.btn_copy.pack(side=LEFT)

    def on_btn_export_csv_click(self):
        """Handle CSV export with file dialog"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export to CSV"
            )
            if filename:
                self.tableview.export_all_records(filename)
                messagebox.showinfo("Success", "Data exported successfully!")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data: {str(e)}")

    def on_btn_copy_click(self):
        """Handle file copy with progress tracking"""
        target_folder = filedialog.askdirectory(title="Select Destination Folder")
        if not target_folder:
            return

        overwrite = messagebox.askyesno(
            "Overwrite Files",
            "Do you want to overwrite existing files?",
            icon="warning"
        )
        
        rename_with_metadata = self.rename_var.get()
        
        # Disable UI elements during copy
        self._set_ui_state(False)
        
        # Configure progress bar
        self.progressbar.config(
            mode="determinate",
            maximum=len(self.finder.validated_pdf_files),
            value=0
        )
        
        # Start copy operation in background
        threading.Thread(
            target=self._run_copy,
            args=(target_folder, overwrite, rename_with_metadata),
            daemon=True
        ).start()

    def on_btn_pick_folder_click(self):
        """Handle folder selection with validation"""
        folder_selected = filedialog.askdirectory(title="Select Search Folder")
        if folder_selected:
            self.etr_folder.delete(0, END)
            self.etr_folder.insert(0, folder_selected)
            self.finder.current_folder = folder_selected

    def on_btn_find_click(self):
        """Handle search operation with validation"""
        self.folder_selected = self.etr_folder.get()
        if not os.path.exists(self.folder_selected):
            messagebox.showerror(
                "Invalid Folder",
                f"Folder not found: {self.folder_selected}",
                icon="error"
            )
            return

        # Disable UI elements during search
        self._set_ui_state(False)
        
        # Configure finder filters
        self.finder.file_size_filter = self.pdf_size_translate[self.cmb_pdf_size.get()]
        self.finder.page_size_filter = self.page_size_translate[self.cmb_page_size.get()]
        
        # Start search operation in background
        threading.Thread(target=self._run_find, daemon=True).start()

    def _set_ui_state(self, enabled: bool):
        """Enable/disable UI elements during operations"""
        state = NORMAL if enabled else DISABLED
        self.btn_find.config(state=state)
        self.btn_copy.config(state=state)
        self.btn_export_csv.config(state=state)
        self.btn_pick_folder.config(state=state)
        self.etr_folder.config(state=state)
        self.cmb_page_size.config(state="readonly" if enabled else DISABLED)
        self.cmb_pdf_size.config(state="readonly" if enabled else DISABLED)
        self.cmb_detect_duplicates.config(state="readonly" if enabled else DISABLED)

    def _run_copy(self, target_folder: str, overwrite: bool, rename_with_metadata: bool = False) -> None:
        """Execute copy operation with progress tracking"""
        try:
            self.finder.copy_files(
                target_folder,
                overwrite,
                FileCopyObserver(self.progressbar, self.lbl_progress),
                rename_with_metadata
            )
            messagebox.showinfo("Success", "Files copied successfully!")
        except Exception as e:
            messagebox.showerror("Copy Error", f"Failed to copy files: {str(e)}")
        finally:
            self._set_ui_state(True)

    def _run_find(self):
        """Execute search operation with progress tracking"""
        try:
            print(f"Finding PDFs in {self.etr_folder.get()}...")
            observer = FileFinderObserver(self.progressbar, self.lbl_progress)
            
            # Clear previous results
            self.tableview.delete_rows()
            
            # Find and validate PDFs
            self.finder.find_all_pdf_files(self.etr_folder.get(), observer)
            detect_duplicates = self.cmb_detect_duplicates.get() == "YES"
            
            if len(self.finder.pdf_files) > 0:
                observer.counter = 0
                self.progressbar.config(
                    mode="determinate",
                    maximum=len(self.finder.pdf_files),
                    value=0
                )
                
                # Validate PDFs
                self.finder.validate_pdfs(observer, detect_duplicates=detect_duplicates)
                self.finder.validated_pdf_files.sort(key=lambda x: x["size"], reverse=True)
                
                # Process results
                seen_hashes = set()
                filtered_files = []
                
                if detect_duplicates:
                    duplicate_count = 0
                    for item in self.finder.validated_pdf_files:
                        file_hash = item.get("hash")
                        if file_hash in seen_hashes:
                            duplicate_count += 1
                            logging.info(f"{duplicate_count} - Duplicate PDF rejected: {item['fullname']}")
                            continue
                        if file_hash and file_hash != "ERROR":
                            seen_hashes.add(file_hash)
                            filtered_files.append(item)
                else:
                    filtered_files = self.finder.validated_pdf_files

                # Update table
                self.tableview.pack_forget()
                for item in filtered_files:
                    filename = f"{Path(item['fullname']).stem + '.pdf'}"
                    formatted_size = self.finder.convert_size(item["size"])
                    self.tableview.insert_row(
                        "end",
                        (formatted_size, item["pages"], filename, item["fullname"])
                    )
                self.tableview.pack(fill=BOTH, expand=YES)
                
                # Enable action buttons
                self.btn_copy.config(state=NORMAL)
                self.btn_export_csv.config(state=NORMAL)
                
                # Show summary
                messagebox.showinfo(
                    "Search Complete",
                    f"Found {len(filtered_files)} PDF files matching your criteria."
                )
        except Exception as e:
            messagebox.showerror("Search Error", f"An error occurred during search: {str(e)}")
        finally:
            self._set_ui_state(True)


class FileFinderObserver(CallBack):
    def __init__(self, progress_bar: tkb.Progressbar, label: tkb.Label) -> None:
        self.progress_bar = progress_bar
        self.label = label
        self.counter = 0

    def update(self, type: int, message: str) -> None:
        self.counter += 1
        self.label.config(text=message)
        self.progress_bar.step()
        print(f" >> {self.counter} - {message}")


class FileCopyObserver(CallBack):
    def __init__(self, progress_bar: tkb.Progressbar, label: tkb.Label) -> None:
        self.progress_bar = progress_bar
        self.label = label
        self.counter = 0

    def update(self, type: int, message: str) -> None:
        self.counter += 1
        self.label.config(text=message)
        self.progress_bar.step()
        print(f" >> {self.counter} - {message}")


if __name__ == "__main__":
    root = tkb.Window("PDFCrawler")
    app = PDFCrawler(root)
    root.mainloop()
