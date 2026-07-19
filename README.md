# pdfcrawler

A GUI tool to find, filter, and organize PDF files from your filesystem.

## Features

- **Recursive search** — walks directory trees to find all PDF files
- **Smart filtering** — filter by minimum page count and file size
- **Duplicate detection** — identifies duplicate files using xxHash
- **CSV export** — export search results to CSV with title, author, pages, size, path, and hash
- **Selective copy** — manually select which PDFs to copy to a destination folder
- **Metadata extraction** — reads PDF metadata (title, author, subject, etc.)
- **Sortable table** — click column headers to sort results
- **In-table search** — filter results as you type
- **Dark/light theme** — toggle between themes, preference is saved
- **Keyboard shortcuts** — fast navigation with Ctrl+F, Ctrl+O, Ctrl+C, Ctrl+E
- **Recent folders** — quick access to recently used search and destination folders
- **Cancellation** — cancel long operations gracefully (finishes current item)
- **Deterministic progress** — progress bar shows exact count (e.g. "23/42")

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

1. Select a **search folder** (type the path, click Browse, or pick from recent folders)
2. Set filter criteria — **min pages** and **min file size**
3. Toggle **duplicate detection** (enabled by default)
4. Click **Search**
5. Review results in the table, use the **Filter** field to narrow results
6. Select files manually (click checkboxes or use Select All / Deselect All)
7. Click **Copy Selected...** to choose a destination and copy
8. Click **Export CSV** to save results to a file

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` | Focus search/filter field |
| `Ctrl+O` | Open folder browser |
| `Ctrl+C` | Copy selected files |
| `Ctrl+E` | Export CSV |
| `Ctrl+A` | Select all visible items |
| `Space` | Toggle selection on focused item |
| `Enter` | Start search (when folder field is focused) |

## Project Structure

- `pdfcrawler.py` — GUI application (entry point)
- `engine.py` — Business logic: `Finder`, `PdfEntry`, `CallBack`
- `test_engine.py` — Tests for engine module
- `test_gui.py` — Tests for SettingsManager and GUI components
- `CONTEXT.md` — Domain model and ubiquitous language
- `playground.py` — Development/testing script (not portable)

## Settings

User settings are stored in `~/.pdfcrawler/settings.json`:

- **Recent search folders** — up to 8 most recent search paths
- **Frequent destination folders** — up to 5 most recent copy destinations
- **Theme preference** — darkly (dark) or cosmo (light)

## License

This project is licensed under the GNU General Public License v3.0 — see the [LICENSE](LICENSE) file for details.
