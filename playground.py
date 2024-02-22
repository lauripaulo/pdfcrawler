from engine import Finder, CallBack
import logging
import os

logging.basicConfig(level=logging.DEBUG)

### This is a playground for testing and debugging purposes. ###
if __name__ == "__main__":
    logging.info("Finding pdfs...")
    path = "C:\\Users\\lauri\\Google Drive\\Pessoal\\# RPG"
    #path = "C:\\"
    finder : Finder = Finder()
    callback : CallBack = CallBack()
    files = finder.find_all_pdf_files(path, callback=callback)
    pdf_files = finder.validate_pdfs(callback=callback)
    finder.save_to_csv(os.path.join(os.getcwd(), "pdfs.txt"))