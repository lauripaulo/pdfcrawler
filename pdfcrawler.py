import logging
import threading
from pathlib import Path
from tkinter import *
from turtle import color

import ttkbootstrap as tkb
from ttkbootstrap.constants import *
from ttkbootstrap.tableview import Tableview

from engine import (CALLBACK_FILE_FOUND, CALLBACK_FILE_VALIDATED, CallBack,
                    Finder)


class PDFCrawler(tkb.Window):

    def __init__(self, root: tkb.Window):
        root.geometry("1024x800")
        root.maxsize(1024, 800)

        self.page_size_options = ["All", ">5", ">10", '>20']
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
            {"text": "File", "width": 824, "anchor": "w"},
            {"text": "Full path", "width": 800, "anchor": "w"}
        ]
        self.tableview: Tableview = Tableview(
            master=root,
            coldata=headings,
            paginated=True,
            pagesize=15,
            searchable=True,
            bootstyle=PRIMARY,
            stripecolor=(colors.light, colors.dark)
        )
        self.tableview.pack(fill=BOTH, expand=YES, padx=5, pady=5)

    def create_progressbar(self, root: tkb.Window):
        self.progressbar = tkb.Progressbar(
            master=root,
            mode=INDETERMINATE,
            bootstyle=(SUCCESS)
        )
        self.progressbar.pack(fill=X, padx=5, pady=5)
        self.lbl_progress = tkb.Label(root, text="Waiting to start...")
        self.lbl_progress.pack(pady=5, padx=5)

    def create_frame_folder(self, root: tkb.Window):
        self.frame_folder: tkb.Frame = tkb.Frame(root)
        self.lbl_folder = tkb.Label(
            self.frame_folder,
            text="Folder:",
            width=10
        )
        self.lbl_folder.pack(side=LEFT, pady=5, padx=5)
        self.etr_folder = tkb.Entry(
            self.frame_folder
        )
        self.etr_folder.insert(0, self.finder.get_current_folder())
        self.etr_folder.pack(side=LEFT, pady=5, padx=5, fill=X, expand=YES)
        self.btn_pick_folder = tkb.Button(
            self.frame_folder,
            text="Choose folder",
            bootstyle="primary",
            command=self.on_btn_pick_folder_click
        )
        self.btn_pick_folder.pack(side=LEFT, pady=5, padx=5)
        self.frame_folder.pack(anchor=W, fill=X, padx=5, pady=5)

    def create_frame_filters(self, root: tkb.Window):
        self.frame_filters: tkb.Frame = tkb.Frame(root)
        self.lbl_pages = tkb.Label(
            self.frame_filters,
            text="Num. pages:",
            width=10
        )
        self.lbl_pages.pack(side=LEFT, pady=5, padx=5)
        self.cmb_page_size = tkb.Combobox(
            self.frame_filters,
            values=self.page_size_options,
            width=10
        )
        self.cmb_page_size.current(0)
        self.cmb_page_size.state(["readonly"])
        self.cmb_page_size.pack(side=LEFT, pady=5, padx=5)
        self.lbl_pdf_size = tkb.Label(
            self.frame_filters,
            text="PDF size:",
            width=10
        )
        self.lbl_pdf_size.pack(side=LEFT, pady=5, padx=5)
        self.cmb_pdf_size = tkb.Combobox(
            self.frame_filters,
            values=self.pdf_size_options,
            width=10
        )
        self.cmb_pdf_size.current(0)
        self.cmb_pdf_size.state(["readonly"])
        self.cmb_pdf_size.pack(side=LEFT, pady=5, padx=5)
        self.btn_find = tkb.Button(
            self.frame_filters,
            text="Start search",
            bootstyle="success",
            command=self.on_btn_find_click
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
            state=DISABLED
        )
        self.btn_export_csv.pack(side=LEFT, pady=5, padx=5)
        self.btn_copy = tkb.Button(
            self.frame_actions,
            text="Copy files to...",
            bootstyle="success",
            command=self.on_btn_copy_click,
            state=DISABLED
        )
        self.btn_copy.pack(side=LEFT, pady=5, padx=5)
        self.frame_actions.pack(anchor=E, fill=X, padx=5, pady=5)

    def on_btn_export_csv_click(self):
        print("Exporting to CSV...")

    def on_btn_copy_click(self):
        print("Copying files...")

    def on_btn_pick_folder_click(self):
        print("Picking folder...")

    def on_btn_find_click(self):
        self.btn_find.config(state=DISABLED)
        self.btn_copy.config(state=DISABLED)
        self.btn_export_csv.config(state=DISABLED)
        self.btn_pick_folder.config(state=DISABLED)
        threading.Thread(target=self._run_find).start()

    def _run_find(self):
        print(f"Finding PDFs in {self.etr_folder.get()}...")
        observer: CallBack = FileFinderObserver(
            self.progressbar, self.lbl_progress)
        self.finder.find_all_pdf_files(self.etr_folder.get(), observer)
        if len(self.finder.pdf_files) > 0:
            observer.counter = 0
            self.progressbar.config(
                mode="determinate",
                maximum=len(self.finder.pdf_files) + 1
            )
            self.progressbar.value = 0
            self.finder.validate_pdfs(observer)
            self.finder.validated_pdf_files.sort(
                key=lambda x: x["size"], reverse=True)
            for item in self.finder.validated_pdf_files:
                filename = f"{Path(item['fullname']).stem + '.pdf'}"
                formatted_size = self.finder.convert_size(item["size"])
                self.tableview.insert_row(
                    'end',
                    (
                        formatted_size,
                        item["pages"],
                        filename,
                        item['fullname']
                    )
                )
            self.tableview.load_table_data()
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


if __name__ == "__main__":
    root = tkb.Window("PDFCrawler")
    app = PDFCrawler(root)
    root.mainloop()
