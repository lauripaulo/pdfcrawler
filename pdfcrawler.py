import ttkbootstrap as tkb
from ttkbootstrap.constants import *
from tkinter import *


class PDFCrawler(tkb.Window):

    def __init__(self, root: tkb.Window):
        root.geometry("1024x600")
        root.maxsize(1024, 600)

        self.page_size_options = ["All", ">5", ">10", '>20']
        self.pdf_size_options = ["All", ">1MB", ">5MB", ">10MB"]

        self.create_frame_folder(root)
        self.create_frame_filters(root)
        self.create_progressbar(root)
        self.create_table_result(root)

    def create_table_result(self, root: tkb.Window):
        self.tbl_results = tkb.Treeview(
            master=root,
            columns=[0, 1, 2, 3],
            show=HEADINGS
        )
        self.tbl_results.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        self.tbl_results.heading(0, text="Size")
        self.tbl_results.heading(1, text="Pages")
        self.tbl_results.heading(2, text="File")
        self.tbl_results.heading(3, text="Info")
        self.tbl_results.column(
            column=0,
            width=100,
            stretch=NO,
            anchor=W
        )
        self.tbl_results.column(
            column=1,
            width=100,
            stretch=NO,
            anchor=W
        )
        self.tbl_results.column(
            column=2,
            width=400,
            stretch=NO,
            anchor=W
        )
        self.tbl_results.column(
            column=3,
            width=400,
            stretch=NO,
            anchor=W
        )

    def create_progressbar(self, root: tkb.Window):
        self.progressbar = tkb.Progressbar(
            master=root,
            mode=INDETERMINATE,
            bootstyle=(STRIPED, SUCCESS)
        )
        self.progressbar.pack(fill=X, expand=FALSE, padx=10, pady=10)
        self.lbl_progress = tkb.Label(root, text="Waiting to start...")
        self.lbl_progress.pack(pady=10, padx=10)

    def create_frame_folder(self, root: tkb.Window):
        self.frame_folder: tkb.Frame = tkb.Frame(root)
        self.lbl_folder = tkb.Label(
            self.frame_folder, text="Folder:", width=10)
        self.lbl_folder.pack(side=LEFT, pady=10, padx=10)
        self.etr_folder = tkb.Entry(self.frame_folder, textvariable="folder")
        self.etr_folder.pack(side=LEFT, pady=10, padx=10)
        self.btn_find = tkb.Button(
            self.frame_folder, text="Choose folder", bootstyle="primary")
        self.btn_find.pack(side=LEFT, pady=10, padx=10)
        self.btn_find = tkb.Button(
            self.frame_folder, text="Start search", bootstyle="success")
        self.btn_find.pack(side=LEFT, pady=10, padx=10)
        self.frame_folder.pack()

    def create_frame_filters(self, root: tkb.Window):
        self.frame_filters: tkb.Frame = tkb.Frame(root)
        self.lbl_pages = tkb.Label(
            self.frame_filters, text="Num. pages:", width=10)
        self.lbl_pages.pack(side=LEFT, pady=10, padx=10)
        self.cmb_page_size = tkb.Combobox(
            self.frame_filters, values=self.page_size_options, width=10)
        self.cmb_page_size.current(0)
        self.cmb_page_size.state(["readonly"])
        self.cmb_page_size.pack(side=LEFT, pady=10, padx=10)
        self.lbl_pdf_size = tkb.Label(
            self.frame_filters, text="PDF size:", width=10)
        self.lbl_pdf_size.pack(side=LEFT, pady=10, padx=10)
        self.cmb_pdf_size = tkb.Combobox(
            self.frame_filters, values=self.pdf_size_options, width=10)
        self.cmb_pdf_size.current(0)
        self.cmb_pdf_size.state(["readonly"])
        self.cmb_pdf_size.pack(side=LEFT, pady=10, padx=10)
        self.frame_filters.pack()


if __name__ == "__main__":
    root = tkb.Window("PDFCrawler")
    app = PDFCrawler(root)
    root.mainloop()
