import engine as eng
import logging
import os

logging.basicConfig(level=logging.DEBUG)

### This is a playground for testing and debugging purposes. ###
if __name__ == "__main__":
    logging.info("Finding pdfs...")
    path = "C:\\Users\\lauri\\Google Drive\\Pessoal\\# RPG"
    files = eng.find_all_pdf_files(path)
    pdf_files = eng.validate_pdfs(files)
    eng.save_to_csv(pdf_files, os.path.join(os.getcwd(), "pdfs.txt"))