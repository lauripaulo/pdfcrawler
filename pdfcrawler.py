import ttkbootstrap as tkb
from ttkbootstrap.constants import *
from tkinter import *


def build_frame_folders(root: tkb.Window):
    frame: tkb.Frame = tkb.Frame(root)
    lbl_folder = tkb.Label(frame, text="Folder:")
    lbl_folder.pack(side=LEFT, pady=10, padx=10)
    etr_folder = tkb.Entry(frame, textvariable="folder")
    etr_folder.pack(side=LEFT, pady=10, padx=10)
    btn_find = tkb.Button(frame, text="Choose folder", bootstyle="primary")
    btn_find.pack(side=LEFT, pady=10, padx=10)
    btn_find = tkb.Button(frame, text="Start search", bootstyle="success")
    btn_find.pack(side=LEFT, pady=10, padx=10)
    frame.pack()


def build_filters_frame(root: tkb.Window):
    page_size_options = [">5", ">10", '>20']
    pdf_size_options = [">1MB", ">5MB", ">10MB"]
    frame: tkb.Frame = tkb.Frame(root)
    lbl_pages = tkb.Label(frame, text="Num. pages:")
    lbl_pages.pack(side=LEFT, pady=10, padx=10)
    cmb_page_size = tkb.Combobox(frame, values=page_size_options)
    cmb_page_size.pack(side=LEFT, pady=10, padx=10)
    lbl_pdf_size = tkb.Label(frame, text="PDF size:")
    lbl_pdf_size.pack(side=LEFT, pady=10, padx=10)
    cmb_pdf_size = tkb.Combobox(frame, values=pdf_size_options)
    cmb_pdf_size.pack(side=LEFT, pady=10, padx=10)
    frame.pack()


def start_app(root: tkb.Window):
    labelHello = tkb.Label(root, text="PDFCrawler - Version 0.0.1")
    labelHello.pack(pady=10, padx=10)
    build_frame_folders(root)
    build_filters_frame(root)


if __name__ == "__main__":
    root = tkb.Window("system")
    root.geometry("640x480")
    root.maxsize(640, 480)
    start_app(root)
    root.mainloop()
