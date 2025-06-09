from ast import Call
from gc import callbacks
import os
import logging
import threading
from pathlib import Path
from tkinter import X, Y, BOTH, DISABLED, END, E, W, YES, LEFT, RIGHT
from tkinter import filedialog, messagebox

import ttkbootstrap as tkb
from ttkbootstrap.constants import PRIMARY, SUCCESS, INDETERMINATE, NORMAL
from ttkbootstrap.tableview import Tableview

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
        root.geometry("1024x700")
        root.maxsize(1024, 700)

        self.page_size_options = ["All", ">5", ">10", ">20"]
        self.pdf_size_options = ["All", ">1MB", ">5MB", ">10MB"]
        self.finder = Finder()

        self.create_frame_folder(root)
        self.create_frame_filters(root)
        self.create_progressbar(root)
        self.create_tableview(root)
        self.create_action_menu(root)

    def create_tableview(self, root: tkb.Window):
        colors = root.style.colors
        headings: list = [
            {"text": "Size", "width": 100, "anchor": "w"},
            {"text": "Pages", "width": 100, "anchor": "w"},
            {"text": "File", "width": 450, "anchor": "w"},
            {"text": "Full path", "width": 800, "anchor": "w"},
        ]
        self.tableview: Tableview = Tableview(
            master=root,
            coldata=headings,
            searchable=True,
            bootstyle=PRIMARY,
            paginated=True,
            stripecolor=(colors.light, colors.dark),
        )
        self.tableview.pack(fill=X, padx=5, pady=5)

    def create_progressbar(self, root: tkb.Window):
        self.progressbar = tkb.Progressbar(
            master=root, mode=INDETERMINATE, bootstyle=(SUCCESS)
        )
        self.progressbar.pack(fill=X, padx=5, pady=5)
        self.lbl_progress = tkb.Label(root, text="Waiting to start...")
        self.lbl_progress.pack(pady=5, padx=5)

    def create_frame_folder(self, root: tkb.Window):
        self.frame_folder: tkb.Frame = tkb.Frame(root)
        self.lbl_folder = tkb.Label(self.frame_folder, text="Folder:", width=10)
        self.lbl_folder.pack(side=LEFT, pady=5, padx=5)
        self.etr_folder = tkb.Entry(self.frame_folder)
        self.etr_folder.insert(0, self.finder.get_current_folder())
        self.etr_folder.pack(side=LEFT, pady=5, padx=5, fill=X, expand=YES)
        self.btn_pick_folder = tkb.Button(
            self.frame_folder,
            text="Choose folder",
            bootstyle="primary",
            command=self.on_btn_pick_folder_click,
        )
        self.btn_pick_folder.pack(side=LEFT, pady=5, padx=5)
        self.frame_folder.pack(anchor=W, fill=X, padx=5, pady=5)

    def create_frame_filters(self, root: tkb.Window):
        self.frame_filters: tkb.Frame = tkb.Frame(root)
        self.lbl_pages = tkb.Label(self.frame_filters, text="Num. pages:", width=10)
        self.lbl_pages.pack(side=LEFT, pady=5, padx=5)
        self.cmb_page_size = tkb.Combobox(
            self.frame_filters, values=self.page_size_options, width=10
        )
        self.cmb_page_size.current(0)
        self.cmb_page_size.state(["readonly"])
        self.cmb_page_size.pack(side=LEFT, pady=5, padx=5)
        self.lbl_pdf_size = tkb.Label(self.frame_filters, text="PDF size:", width=10)
        self.lbl_pdf_size.pack(side=LEFT, pady=5, padx=5)
        self.cmb_pdf_size = tkb.Combobox(
            self.frame_filters, values=self.pdf_size_options, width=10
        )
        self.cmb_pdf_size.current(0)
        self.cmb_pdf_size.state(["readonly"])
        self.cmb_pdf_size.pack(side=LEFT, pady=5, padx=5)
        # --- New code for Detect duplicates ---
        self.lbl_detect_duplicates = tkb.Label(self.frame_filters, text="Detect duplicates:", width=16)
        self.lbl_detect_duplicates.pack(side=LEFT, pady=5, padx=5)
        self.cmb_detect_duplicates = tkb.Combobox(
            self.frame_filters, values=["YES", "NO"], width=5
        )
        self.cmb_detect_duplicates.current(1)  # "NO" as default
        self.cmb_detect_duplicates.state(["readonly"])
        self.cmb_detect_duplicates.pack(side=LEFT, pady=5, padx=5)
        # --- End new code ---
        self.btn_find = tkb.Button(
            self.frame_filters,
            text="Start search",
            bootstyle="success",
            command=self.on_btn_find_click,
        )
        self.btn_find.pack(side=LEFT, pady=5, padx=5)
        self.frame_filters.pack(anchor=W, fill=X, padx=5, pady=5)

    def create_action_menu(self, root: tkb.Window):
        self.frame_actions: tkb.Frame = tkb.Frame(root)
        self.btn_export_csv = tkb.Button(
            self.frame_actions,
            text="Export to CSV",
            bootstyle="primary",
            command=self.on_btn_export_csv_click,
            state=DISABLED,
        )
        self.btn_export_csv.pack(side=LEFT, pady=5, padx=5)
        self.btn_copy = tkb.Button(
            self.frame_actions,
            text="Copy files to...",
            bootstyle="success",
            command=self.on_btn_copy_click,
            state=DISABLED,
        )
        self.btn_copy.pack(side=LEFT, pady=5, padx=5)
        # --- New: Add checkbox for renaming files with title/author ---
        self.rename_var = tkb.BooleanVar(value=False)
        self.chk_rename = tkb.Checkbutton(
            self.frame_actions,
            text="Rename with Title & Author",
            variable=self.rename_var,
            bootstyle="info",
        )
        self.chk_rename.pack(side=LEFT, pady=5, padx=5)
        # --- End new code ---
        self.frame_actions.pack(anchor=E, fill=X, padx=5, pady=5)

    def on_btn_export_csv_click(self):
        print("Exporting to CSV...")
        self.tableview.export_all_records()

    def on_btn_copy_click(self):
        print("Copying files...")
        target_folder: str = filedialog.askdirectory()
        overwrite: bool = messagebox.askyesno("Overwrite files", "Overwrite files?")
        rename_with_metadata: bool = self.rename_var.get()
        if target_folder:
            self.progressbar.config(
                mode="determinate",
                maximum=len(self.finder.validated_pdf_files),
                value=0,
            )
            self.btn_copy.config(state=DISABLED)
            self.btn_export_csv.config(state=DISABLED)
            self.btn_pick_folder.config(state=DISABLED)
            threading.Thread(
                target=self._run_copy,
                args=(
                    target_folder,
                    overwrite,
                    rename_with_metadata,  # Pass the new option
                ),
            ).start()

    def on_btn_pick_folder_click(self):
        print("Picking folder...")
        folder_selected = filedialog.askdirectory()
        self.etr_folder.delete(0, END)
        self.etr_folder.insert(0, folder_selected)
        self.finder.current_folder = folder_selected
        print(f"Picked folder: {folder_selected}")

    def on_btn_find_click(self):
        self.folder_selected = self.etr_folder.get()
        if os.path.exists(self.folder_selected):
            self.btn_find.config(state=DISABLED)
            self.btn_copy.config(state=DISABLED)
            self.btn_export_csv.config(state=DISABLED)
            self.btn_pick_folder.config(state=DISABLED)
            self.finder.file_size_filter = self.pdf_size_translate[
                self.cmb_pdf_size.get()
            ]
            self.finder.page_size_filter = self.page_size_translate[
                self.cmb_page_size.get()
            ]
            threading.Thread(target=self._run_find).start()
        else:
            print(f"Folder {self.folder_selected} not found!")
            messagebox.showerror(
                "Folder not found", f"Folder {self.folder_selected} not found!"
            )

    def _run_copy(self, target_folder: str, overwrite: bool, rename_with_metadata: bool = False) -> None:
        self.finder.copy_files(
            target_folder,
            overwrite,
            FileCopyObserver(self.progressbar, self.lbl_progress),
            rename_with_metadata,  # Pass to Finder
        )

    def _run_find(self):
        print(f"Finding PDFs in {self.etr_folder.get()}...")
        observer: CallBack = FileFinderObserver(self.progressbar, self.lbl_progress)
        self.finder.find_all_pdf_files(self.etr_folder.get(), observer)
        # Clear previous table data before inserting new rows
        self.tableview.delete_rows()
        detect_duplicates = self.cmb_detect_duplicates.get() == "YES"
        if len(self.finder.pdf_files) > 0:
            observer.counter = 0
            self.progressbar.config(
                mode="determinate", maximum=len(self.finder.pdf_files), value=0
            )
            self.finder.validate_pdfs(observer, detect_duplicates=detect_duplicates)
            self.finder.validated_pdf_files.sort(key=lambda x: x["size"], reverse=True)
            print(f" >> Total: {len(self.finder.pdf_files)} / step: {observer.counter}")
            seen_hashes = set()
            filtered_files = []
            if detect_duplicates:
                duplicate_count = 0
                for item in self.finder.validated_pdf_files:
                    # --- Remove duplicates if enabled ---
                    file_hash = item.get("sha256")
                    if file_hash in seen_hashes:
                        duplicate_count += 1
                        logging.info(f"{duplicate_count} - Duplicate PDF rejected: {item['fullname']}")
                        continue
                    if file_hash and file_hash != "ERROR":
                        seen_hashes.add(file_hash)
                        filtered_files.append(item)
            # Show only filtered files in the table
            # Temporarily hide the tableview to prevent UI updates during insertion
            self.tableview.pack_forget()
            for item in filtered_files:
                filename = f"{Path(item['fullname']).stem + '.pdf'}"
                formatted_size = self.finder.convert_size(item["size"])
                self.tableview.insert_row(
                    "end", (formatted_size, item["pages"], filename, item["fullname"])
                )
            # Re-display the tableview after all rows are inserted
            self.tableview.pack(fill=X, padx=5, pady=5)
            self.btn_copy.config(state=NORMAL)
            self.btn_export_csv.config(state=NORMAL)
        self.btn_find.config(state=NORMAL)


class FileFinderObserver(CallBack):

    def __init__(self, progress_bar: tkb.Progressbar, label: tkb.Label) -> None:
        self.progress_bar: tkb.Progressbar = progress_bar
        self.label: tkb.Label = label
        self.counter: int = 0

    def update(self, type: int, message: str) -> None:
        self.counter += 1
        self.label.config(text=message)
        self.progress_bar.step()
        print(f" >> {self.counter} - {message}")


class FileCopyObserver(CallBack):
    def __init__(self, progress_bar: tkb.Progressbar, label: tkb.Label) -> None:
        self.progress_bar: tkb.Progressbar = progress_bar
        self.label: tkb.Label = label
        self.counter: int = 0

    def update(self, type: int, message: str) -> None:
        self.counter += 1
        self.label.config(text=message)
        self.progress_bar.step()
        print(f" >> {self.counter} - {message}")


if __name__ == "__main__":
    root = tkb.Window("PDFCrawler")
    app = PDFCrawler(root)
    root.mainloop()
