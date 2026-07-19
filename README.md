# pdfcrawler

A GUI tool to find, filter, and organize PDF files from your filesystem.

## Features

- **Recursive search** — walks directory trees to find all PDF files
- **Smart filtering** — filter by minimum page count and file size
- **Duplicate detection** — identifies duplicate files using xxHash
- **CSV export** — export search results to CSV for further analysis
- **Copy/move files** — copy found PDFs to a target directory with optional renaming
- **Metadata extraction** — reads PDF metadata (title, author, subject, etc.)

## Requirements

- Python 3.x
- GUI support (tkinter)

## Installation

```bash
pip install -r requirements.txt
```

### Linux (openSUSE Tumbleweed)

If tkinter is not available, install it with:

```bash
zypper install python311-tk
```

## Usage

```bash
python pdfcrawler.py
```

1. Click **Browse...** to select a folder to search
2. Set your filter criteria (min pages, min file size)
3. Choose whether to enable duplicate detection
4. Click **Start Search**
5. Review results in the table below

## Actions

After a search completes:

- **Export to CSV** — saves results to a CSV file
- **Copy Files To...** — copies selected PDFs to a destination folder
  - Optional: Rename files using PDF title and author metadata

## Project Structure

- `pdfcrawler.py` — GUI application (entry point)
- `engine.py` — Business logic for PDF discovery and processing
- `playground.py` — Development/testing script (not portable)

## License

This project is licensed under the GNU General Public License v3.0 — see the [LICENSE](LICENSE) file for details.
