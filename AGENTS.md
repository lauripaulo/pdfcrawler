# AGENTS.md

## Project overview

pdfcrawler is a small Python GUI app (tkinter + ttkbootstrap) that walks a directory tree, finds PDF files, filters by page count and file size, detects duplicates via xxHash, and copies/moves them. Licensed GPLv3.

## Run

```
pip install -r requirements.txt
python pdfcrawler.py
```

`playground.py` is a scratch script for testing engine logic. It has a hardcoded Windows path — do not treat it as portable.

## Architecture

Two modules:

- **`engine.py`** — `Finder` class. Pure business logic: file discovery, PDF metadata extraction (PyPDF2), duplicate detection (xxhash), CSV export, file copy.
- **`pdfcrawler.py`** — `PDFCrawler` class. ttkbootstrap GUI. Instantiates `Finder`, wires up callbacks, handles user actions.

There is no `__init__.py`, no package structure, no tests, no CI, no lint/typecheck config.

## Key quirks

- `Finder` uses **class-level mutable state** (`pdf_files = []`, `validated_pdf_files = []`, `file_size_filter`, `page_size_filter`). These are shared across every instance of the class. New code that instantiates `Finder` multiple times will clobber previous results.
- `requirements.txt` mixes runtime deps (`PyPDF2`, `ttkbootstrap`, `xxhash`, `pycryptodome`, `pillow`) with dev tools (`black`, `ruff`, `mypy-extensions`, `click`, `colorama`, `packaging`, `pathspec`, `pep8`, `platformdirs`).
- Linux (openSUSE Tumbleweed): `zypper install python311-tk` is required for tkinter.
- `engine.py:188` — `_sanitize_filename` replaces `< > : " / \ | ? *` with `_` and strips leading dots/spaces.
