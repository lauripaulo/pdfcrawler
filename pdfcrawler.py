import os
import json
import logging
import threading
from pathlib import Path
from tkinter import font as tkfont
from tkinter import END, LEFT, RIGHT, BOTTOM, BOTH, X, Y, DISABLED, NORMAL, W, CENTER, TclError
from tkinter import filedialog, messagebox

import ttkbootstrap as tkb
from ttkbootstrap.constants import SUCCESS, INDETERMINATE, INFO, WARNING
from ttkbootstrap.widgets.scrolled import ScrolledFrame

from engine import (
    CallBack,
    Finder,
)

SETTINGS_DIR = Path.home() / ".pdfcrawler"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

RECENT_FOLDERS_KEY = "recent_search_folders"
FREQUENT_DESTINATIONS_KEY = "frequent_destinations"
THEME_KEY = "theme"
MAX_RECENT = 8
MAX_FREQUENT = 5


class SettingsManager:
    """Persist settings to JSON (~/.pdfcrawler/settings.json)."""

    def __init__(self) -> None:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        self._data: dict = {}
        self.load()

    def load(self) -> None:
        if SETTINGS_FILE.exists():
            try:
                self._data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def save(self) -> None:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_recent_folders(self) -> list:
        return self._data.get(RECENT_FOLDERS_KEY, [])

    def add_recent_folder(self, folder: str) -> None:
        folders = self.get_recent_folders()
        if folder in folders:
            folders.remove(folder)
        folders.insert(0, folder)
        self._data[RECENT_FOLDERS_KEY] = folders[:MAX_RECENT]
        self.save()

    def get_frequent_destinations(self) -> list:
        return self._data.get(FREQUENT_DESTINATIONS_KEY, [])

    def add_frequent_destination(self, folder: str) -> None:
        folders = self.get_frequent_destinations()
        if folder in folders:
            folders.remove(folder)
        folders.insert(0, folder)
        self._data[FREQUENT_DESTINATIONS_KEY] = folders[:MAX_FREQUENT]
        self.save()

    def get_theme(self) -> str:
        return self._data.get(THEME_KEY, "darkly")

    def set_theme(self, theme: str) -> None:
        self._data[THEME_KEY] = theme
        self.save()


class PDFCrawler(tkb.Window):
    page_size_options = ["All", ">5", ">10", ">20", ">50"]
    pdf_size_options = ["All", ">1MB", ">5MB", ">10MB", ">50MB"]

    # Column configuration: (id, text, width, anchor, sort_key)
    COLUMNS = [
        ("select", "☐", 40, CENTER, None),
        ("title", "Title", 250, W, "title"),
        ("author", "Author", 150, W, "author"),
        ("pages", "Pages", 70, CENTER, "pages"),
        ("size", "Size", 90, CENTER, "size"),
        ("path", "Path", 300, W, "fullname"),
    ]

    INVALID_TAG = "invalid"
    DUPLICATE_TAG = "duplicate"

    def __init__(self, root: tkb.Window) -> None:
        root.geometry("1280x800")
        root.minsize(900, 600)
        root.title("PDF Crawler")

        self.root = root
        self.finder = Finder()
        self.settings = SettingsManager()

        # Data
        self.all_entries: list = []  # PdfEntry objects in display order
        self.search_query: str = ""
        self.selected_ids: set = set()
        self.sort_column: str = "size"
        self.sort_ascending: bool = False
        self.visible_entry_ids: set[str] = set()
        self.current_search_folder: str | None = None

        # Operation state
        self.ui_busy = False
        self.operation_cancelled = False
        self.operation_thread: threading.Thread | None = None
        self.current_observer: OperationObserver | None = None

        # Apply saved theme
        saved_theme = self.settings.get_theme()
        if saved_theme in tkb.Style().theme_names():
            tkb.Style().theme_use(saved_theme)

        # Build UI
        self._create_menu()
        self._create_top_bar()
        self._create_search_section()
        self._create_progress_section()
        self._create_results_section()
        self._create_status_bar()
        self._bind_shortcuts()

        # Populate recent folders
        self._refresh_recent_folders()
        self._refresh_frequent_destinations()

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _create_menu(self) -> None:
        menubar = tkb.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tkb.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="Export CSV",
            command=self.on_export_csv,
            accelerator="Ctrl+E",
        )
        file_menu.add_command(
            label="Exit",
            command=self.root.quit,
        )

    # ------------------------------------------------------------------
    # Top bar (title + theme toggle)
    # ------------------------------------------------------------------

    def _create_top_bar(self) -> None:
        top = tkb.Frame(self.root)
        top.pack(fill=X, padx=10, pady=(10, 5))

        tkb.Label(
            top,
            text="PDF Crawler",
            font=("Helvetica", 16, "bold"),
        ).pack(side=LEFT)

        tkb.Label(
            top,
            text="— Find and organize your PDFs",
            font=("Helvetica", 10),
        ).pack(side=LEFT, padx=(10, 0))

        # Theme toggle
        theme_frame = tkb.Frame(top)
        theme_frame.pack(side=RIGHT)
        tkb.Label(theme_frame, text="Theme:").pack(side=LEFT, padx=(0, 5))

        self.theme_var = tkb.BooleanVar(
            value=tkb.Style().theme_use() == "darkly"
        )
        self.theme_switch = tkb.Checkbutton(
            theme_frame,
            text="Dark",
            variable=self.theme_var,
            bootstyle="info",
            command=self._on_theme_toggle,
        )
        self.theme_switch.pack(side=LEFT)

    def _on_theme_toggle(self) -> None:
        is_dark = self.theme_var.get()
        new_theme = "darkly" if is_dark else "cosmo"
        try:
            tkb.Style().theme_use(new_theme)
            self.settings.set_theme(new_theme)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Search controls
    # ------------------------------------------------------------------

    def _create_search_section(self) -> None:
        section = tkb.LabelFrame(self.root, text="Search")
        section.pack(fill=X, padx=10, pady=5)

        content = tkb.Frame(section)
        content.pack(fill=X, padx=10, pady=10)

        # Folder row
        folder_row = tkb.Frame(content)
        folder_row.pack(fill=X, pady=(0, 8))

        tkb.Label(folder_row, text="Folder:", width=10, anchor=W).pack(
            side=LEFT, padx=(0, 5)
        )
        self.etr_folder = tkb.Entry(folder_row)
        self.etr_folder.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        self.etr_folder.insert(0, Finder.get_current_folder())

        self.btn_browse = tkb.Button(
            folder_row,
            text="Browse...",
            command=self.on_browse_folder,
            width=12,
        )
        self.btn_browse.pack(side=LEFT, padx=(0, 10))

        # Recent folders combobox
        self.cmb_recent = tkb.Combobox(
            folder_row,
            values=[],
            width=30,
            state="readonly",
        )
        self.cmb_recent.pack(side=LEFT)
        self.cmb_recent.bind(
            "<<ComboboxSelected>>", self._on_recent_folder_selected
        )

        # Filters row
        filters_row = tkb.Frame(content)
        filters_row.pack(fill=X)

        # Page filter
        pg_frame = tkb.Frame(filters_row)
        pg_frame.pack(side=LEFT, padx=(0, 20))
        tkb.Label(pg_frame, text="Pages >:").pack(side=LEFT, padx=(0, 5))
        self.cmb_pages = tkb.Combobox(
            pg_frame,
            values=self.page_size_options,
            state="readonly",
            width=8,
        )
        self.cmb_pages.current(0)
        self.cmb_pages.pack(side=LEFT)

        # Size filter
        sz_frame = tkb.Frame(filters_row)
        sz_frame.pack(side=LEFT, padx=(0, 20))
        tkb.Label(sz_frame, text="Size >:").pack(side=LEFT, padx=(0, 5))
        self.cmb_size = tkb.Combobox(
            sz_frame,
            values=self.pdf_size_options,
            state="readonly",
            width=8,
        )
        self.cmb_size.current(0)
        self.cmb_size.pack(side=LEFT)

        # Duplicate detection
        dup_frame = tkb.Frame(filters_row)
        dup_frame.pack(side=LEFT, padx=(0, 20))
        self.dup_var = tkb.BooleanVar(value=True)
        self.chk_duplicates = tkb.Checkbutton(
            dup_frame,
            text="Detect duplicates",
            variable=self.dup_var,
        )
        self.chk_duplicates.pack(side=LEFT, padx=(0, 5))

        # Buttons
        btn_row = tkb.Frame(filters_row)
        btn_row.pack(side=RIGHT)

        self.btn_search = tkb.Button(
            btn_row,
            text="Search",
            command=self.on_search,
            width=14,
        )
        self.btn_search.pack(side=LEFT, padx=(0, 5))

        self.btn_cancel = tkb.Button(
            btn_row,
            text="Cancel",
            command=self.on_cancel,
            width=12,
            state=DISABLED,
            bootstyle=WARNING,
        )
        self.btn_cancel.pack(side=LEFT)

    # ------------------------------------------------------------------
    # Progress section
    # ------------------------------------------------------------------

    def _create_progress_section(self) -> None:
        section = tkb.Frame(self.root)
        section.pack(fill=X, padx=10, pady=5)

        self.progressbar = tkb.Progressbar(
            section, mode=INDETERMINATE
        )
        self.progressbar.pack(fill=X, pady=(0, 3))

        self.lbl_progress = tkb.Label(
            section,
            text="Ready",
            wraplength=1200,
        )
        self.lbl_progress.pack(fill=X)

    # ------------------------------------------------------------------
    # Results section
    # ------------------------------------------------------------------

    def _create_results_section(self) -> None:
        section = tkb.Frame(self.root)
        section.pack(fill=BOTH, expand=True, padx=10, pady=5)

        # Search/filter entry
        search_row = tkb.Frame(section)
        search_row.pack(fill=X, pady=(0, 3))

        tkb.Label(search_row, text="Filter:").pack(side=LEFT, padx=(0, 5))
        self.etr_search = tkb.Entry(search_row)
        self.etr_search.pack(side=LEFT, fill=X, expand=True)
        self.etr_search.bind("<KeyRelease>", self._on_search_filter)

        # Table
        table_frame = ScrolledFrame(section)
        table_frame.pack(fill=BOTH, expand=True, pady=(3, 5))

        # Build treeview
        self.tree = tkb.Treeview(
            table_frame,
            columns=[c[0] for c in self.COLUMNS],
            show="headings",
            selectmode="extended",
        )

        # Define headings
        col_defs = []
        for col_id, text, width, anchor, sort_key in self.COLUMNS:
            self.tree.heading(
                col_id,
                text=text,
                command=lambda c=col_id: self._on_sort_column(c),
            )
            self.tree.column(col_id, width=width, anchor=anchor)
            col_defs.append(col_id)

        # Vertical scrollbar
        scrollbar = tkb.Scrollbar(
            table_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Layout treeview + scrollbar
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        base_font = tkfont.nametofont("TkDefaultFont")
        invalid_font = base_font.copy()
        invalid_font.configure(overstrike=1)
        self.tree.tag_configure(self.INVALID_TAG, font=invalid_font)
        self.tree.tag_configure(self.DUPLICATE_TAG)

        # Bind double-click for checkbox toggle
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        # Action buttons
        actions = tkb.Frame(section)
        actions.pack(fill=X)

        # Left: select all / deselect all
        sel_frame = tkb.Frame(actions)
        sel_frame.pack(side=LEFT)

        self.btn_select_all = tkb.Button(
            sel_frame,
            text="Select All",
            command=self._on_select_all,
            width=12,
        )
        self.btn_select_all.pack(side=LEFT, padx=(0, 5))

        self.btn_deselect_all = tkb.Button(
            sel_frame,
            text="Deselect All",
            command=self._on_deselect_all,
            width=12,
        )
        self.btn_deselect_all.pack(side=LEFT)

        # Right: copy + export
        dest_frame = tkb.Frame(actions)
        dest_frame.pack(side=RIGHT, padx=(0, 10))

        tkb.Label(dest_frame, text="Destination:").pack(side=LEFT, padx=(0, 5))
        self.cmb_destination = tkb.Combobox(
            dest_frame,
            values=[],
            width=36,
            state="readonly",
        )
        self.cmb_destination.pack(side=LEFT, padx=(0, 5))

        self.btn_dest_browse = tkb.Button(
            dest_frame,
            text="Browse...",
            command=self._on_pick_destination,
            width=11,
        )
        self.btn_dest_browse.pack(side=LEFT)

        act_frame = tkb.Frame(actions)
        act_frame.pack(side=RIGHT)

        self.btn_copy = tkb.Button(
            act_frame,
            text="Copy Selected...",
            command=self.on_copy_selected,
            width=16,
            state=DISABLED,
            bootstyle=SUCCESS,
        )
        self.btn_copy.pack(side=LEFT, padx=(0, 5))

        self.btn_csv = tkb.Button(
            act_frame,
            text="Export CSV",
            command=self.on_export_csv,
            width=14,
            state=DISABLED,
        )
        self.btn_csv.pack(side=LEFT)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _create_status_bar(self) -> None:
        self.status_bar = tkb.Frame(self.root)
        self.status_bar.pack(fill=X, side=BOTTOM, padx=10, pady=(0, 5))

        self.lbl_status_found = tkb.Label(
            self.status_bar, text="Found: 0"
        )
        self.lbl_status_found.pack(side=LEFT, padx=(0, 20))

        self.lbl_status_duplicates = tkb.Label(
            self.status_bar, text="Duplicates: 0"
        )
        self.lbl_status_duplicates.pack(side=LEFT, padx=(0, 20))

        self.lbl_status_selected = tkb.Label(
            self.status_bar, text="Selected: 0"
        )
        self.lbl_status_selected.pack(side=LEFT, padx=(0, 20))

        self.lbl_status_size = tkb.Label(
            self.status_bar, text="Size: 0 B"
        )
        self.lbl_status_size.pack(side=LEFT)

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-f>", self._on_ctrl_f)
        self.root.bind("<Control-F>", self._on_ctrl_f)
        self.root.bind("<Control-o>", self._on_ctrl_o)
        self.root.bind("<Control-O>", self._on_ctrl_o)
        self.root.bind("<Control-c>", self._on_ctrl_c)
        self.root.bind("<Control-C>", self._on_ctrl_c)
        self.root.bind("<Control-e>", self._on_ctrl_e)
        self.root.bind("<Control-E>", self._on_ctrl_e)
        self.root.bind("<Control-a>", self._on_ctrl_a)
        self.root.bind("<Control-A>", self._on_ctrl_a)
        self.root.bind("<space>", self._on_space)
        self.etr_folder.bind("<Return>", self._on_enter_folder)

    def _on_ctrl_f(self, event=None) -> None:
        self.etr_search.focus_set()
        self.etr_search.select_range(0, END)
        return "break"

    def _on_ctrl_o(self, event=None) -> None:
        self.on_browse_folder()
        return "break"

    def _on_ctrl_c(self, event=None) -> None:
        if self.btn_copy.cget("state") != DISABLED:
            self.on_copy_selected()
        return "break"

    def _on_ctrl_e(self, event=None) -> None:
        if self.btn_csv.cget("state") != DISABLED:
            self.on_export_csv()
        return "break"

    def _on_ctrl_a(self, event=None) -> None:
        self._on_select_all()
        return "break"

    def _on_space(self, event=None) -> None:
        """Toggle selection on the currently focused tree item."""
        iid = self.tree.focus()
        if iid:
            self._toggle_selection(iid)
        return "break"

    def _on_enter_folder(self, event=None) -> None:
        self.on_search()
        return "break"

    # ------------------------------------------------------------------
    # Treeview helpers
    # ------------------------------------------------------------------

    def _refresh_recent_folders(self) -> None:
        folders = self.settings.get_recent_folders()
        self.cmb_recent.config(values=folders)
        if folders:
            self.cmb_recent.set(folders[0])

    def _refresh_frequent_destinations(self) -> None:
        folders = self.settings.get_frequent_destinations()
        self.cmb_destination.config(values=folders)
        if folders and not self.cmb_destination.get().strip():
            self.cmb_destination.set(folders[0])

    def _on_pick_destination(self) -> None:
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            self.cmb_destination.set(folder)

    def _on_recent_folder_selected(self, event=None) -> None:
        val = self.cmb_recent.get()
        if val:
            self.etr_folder.delete(0, END)
            self.etr_folder.insert(0, val)

    def _clear_tree(self) -> None:
        existing_ids = set(self.tree.get_children())
        existing_ids.update(entry.fullname for entry in self.all_entries)
        for iid in existing_ids:
            try:
                self.tree.delete(iid)
            except TclError:
                pass

    def _populate_tree(self, entries: list) -> None:
        """Populate the treeview with PdfEntry objects."""
        # Preserve selection
        saved_selection = self.selected_ids.copy()
        self._clear_tree()
        self.all_entries = list(entries)
        self.selected_ids = set()

        for entry in entries:
            iid = entry.fullname  # Use full path as item ID (unique)
            title = entry.info.get("title", "") if entry.info else ""
            author = entry.info.get("author", "") if entry.info else ""
            pages = entry.pages if entry.pages is not None else ""
            size_str = Finder.convert_size(entry.size)
            if self.current_search_folder:
                try:
                    path = str(Path(entry.fullname).relative_to(self.current_search_folder))
                except ValueError:
                    path = Path(entry.fullname).name
            else:
                path = Path(entry.fullname).name
            is_selected = iid in saved_selection
            if is_selected:
                self.selected_ids.add(iid)

            values = (
                "☑" if is_selected else "☐",
                title,
                author,
                pages,
                size_str,
                path,
            )
            tags = []
            if entry.is_duplicate:
                tags.append(self.DUPLICATE_TAG)
            if not entry.is_valid:
                tags.append(self.INVALID_TAG)

            self.tree.insert("", "end", iid=iid, values=values, tags=tuple(tags))

        self.selected_ids &= {entry.fullname for entry in entries}
        self._apply_search_filter()
        self._update_status()

    def _apply_search_filter(self) -> None:
        """Show/hide rows based on search query using Treeview detach/move."""
        query = self.search_query.strip().lower()
        self.visible_entry_ids = set()
        for entry in self.all_entries:
            iid = entry.fullname
            values = self.tree.item(iid, "values")
            haystack = " ".join(str(v).lower() for v in values)
            match = not query or query in haystack
            if match:
                self.tree.move(iid, "", "end")
                self.visible_entry_ids.add(iid)
            else:
                self.tree.detach(iid)

    def _on_search_filter(self, event=None) -> None:
        self.search_query = self.etr_search.get()
        self._apply_search_filter()
        self._update_status()

    def _on_tree_double_click(self, event) -> None:
        """Toggle checkbox when user double-clicks a tree cell."""
        col = self.tree.identify_column(event.x)
        if col == "#1":  # Checkbox column
            iid = self.tree.identify_row(event.y)
            if iid:
                self._toggle_selection(iid)

    def _toggle_selection(self, iid: str) -> None:
        item = self.tree.item(iid)
        values = list(item["values"])

        if iid in self.selected_ids:
            self.selected_ids.discard(iid)
            values[0] = "☐"
        else:
            self.selected_ids.add(iid)
            values[0] = "☑"

        self.tree.item(iid, values=tuple(values))
        self._update_status()

    def _get_selected_entries(self) -> list:
        """Get PdfEntry objects for selected rows."""
        result = []
        for entry in self.all_entries:
            if entry.fullname in self.selected_ids:
                result.append(entry)
        return result

    def _on_select_all(self) -> None:
        for iid in self.tree.get_children():
            values = list(self.tree.item(iid, "values"))
            self.selected_ids.add(iid)
            values[0] = "☑"
            self.tree.item(iid, values=tuple(values))
        self._update_status()

    def _on_deselect_all(self) -> None:
        self.selected_ids = set()
        for iid in self.tree.get_children():
            values = list(self.tree.item(iid, "values"))
            values[0] = "☐"
            self.tree.item(iid, values=tuple(values))
        self._update_status()

    def _on_sort_column(self, col_id: str) -> None:
        if not self.all_entries:
            return

        # Toggle sort direction
        if self.sort_column == col_id:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = col_id
            self.sort_ascending = False

        # Find the sort key from column config
        sort_key = None
        for col_id_def, _, _, _, key in self.COLUMNS:
            if col_id_def == col_id:
                sort_key = key
                break

        if sort_key:
            self.all_entries.sort(
                key=lambda e: (
                    e.__dict__.get(sort_key, "") is None,
                    e.__dict__.get(sort_key, ""),
                ),
                reverse=not self.sort_ascending,
            )
            # Rebuild display (preserves selection via saved_ids restore)
            self._populate_tree(self.all_entries)
            self.selected_ids &= {entry.fullname for entry in self.all_entries}

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _update_status(self) -> None:
        total = len(self.all_entries)
        duplicates = sum(1 for e in self.all_entries if e.is_duplicate)
        selected = len(self.selected_ids)
        selected_size = sum(
            e.size for e in self.all_entries if e.fullname in self.selected_ids
        )

        self.lbl_status_found.config(text=f"Found: {total}")
        self.lbl_status_duplicates.config(text=f"Duplicates: {duplicates}")
        self.lbl_status_selected.config(text=f"Selected: {selected}")
        self.lbl_status_size.config(text=f"Size: {Finder.convert_size(selected_size)}")

    def _clear_results_state(self) -> None:
        self.search_query = ""
        self.etr_search.delete(0, END)
        self.selected_ids = set()
        self.visible_entry_ids = set()
        self._clear_tree()
        self.all_entries = []
        self._update_status()

    # ------------------------------------------------------------------
    # Operation controls
    # ------------------------------------------------------------------

    def _set_ui_busy(self, busy: bool) -> None:
        """Enable/disable controls during operations."""
        self.ui_busy = busy
        state = DISABLED if busy else NORMAL
        ro_state = DISABLED if busy else "readonly"

        self.btn_search.config(state=state)
        self.btn_browse.config(state=state)
        if busy:
            self.btn_copy.config(state=DISABLED)
            self.btn_csv.config(state=DISABLED)
        else:
            has_entries = len(self.all_entries) > 0
            self.btn_copy.config(state=NORMAL if has_entries else DISABLED)
            self.btn_csv.config(state=NORMAL if has_entries else DISABLED)
        self.btn_select_all.config(state=state)
        self.btn_deselect_all.config(state=state)
        self.btn_dest_browse.config(state=state)
        self.chk_duplicates.config(state=state)
        self.etr_folder.config(state=state)
        self.cmb_pages.config(state=ro_state)
        self.cmb_size.config(state=ro_state)
        self.cmb_recent.config(state=ro_state)
        self.cmb_destination.config(state=ro_state)

        if busy:
            self.btn_cancel.config(state=NORMAL)
        else:
            self.btn_cancel.config(state=DISABLED)
            self.operation_cancelled = False
            self.current_observer = None

    def on_cancel(self) -> None:
        self.operation_cancelled = True
        if self.current_observer:
            self.current_observer.cancel()
        self.lbl_progress.config(text="Cancelling...")

    def on_browse_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select Search Folder")
        if folder:
            self.etr_folder.delete(0, END)
            self.etr_folder.insert(0, folder)

    def _parse_page_filter(self) -> int | None:
        val = self.cmb_pages.get()
        if val == "All":
            return None
        return int(val.lstrip(">"))

    def _parse_size_filter(self) -> int | None:
        val = self.cmb_size.get()
        if val == "All":
            return None
        multiplier = {"MB": 1024 * 1024}[val[-2:]]
        return int(val[1:-2]) * multiplier

    # ------------------------------------------------------------------
    # Search operation
    # ------------------------------------------------------------------

    def on_search(self) -> None:
        if self.ui_busy:
            return

        folder = self.etr_folder.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror(
                "Invalid Folder",
                f"Folder not found: {folder}",
                icon="error",
            )
            return

        page_filter = self._parse_page_filter()
        size_filter = self._parse_size_filter()
        detect = self.dup_var.get()
        self.current_search_folder = folder

        # Save to recent
        self.settings.add_recent_folder(folder)
        self._refresh_recent_folders()

        self._clear_results_state()

        # Set up progress
        self.progressbar.config(mode=INDETERMINATE)
        self.progressbar.start(10)
        self.lbl_progress.config(text="Searching...")
        self._set_ui_busy(True)
        self.operation_cancelled = False
        observer = OperationObserver(self)
        self.current_observer = observer

        self.operation_thread = threading.Thread(
            target=self._run_search,
            args=(folder, page_filter, size_filter, detect, observer),
            daemon=True,
        )
        self.operation_thread.start()

    def _run_search(
        self,
        folder: str,
        page_filter: int | None,
        size_filter: int | None,
        detect: bool,
        observer: "OperationObserver",
    ) -> None:
        try:
            # Step 1: Find PDFs
            self._update_progress("Scanning folder for PDFs...")
            pdf_files = self.finder.find_all_pdf_files(folder, observer)

            if self.operation_cancelled:
                self._finish_search()
                return

            if not pdf_files:
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Search Complete", "No PDF files found."
                    ),
                )
                self._finish_search()
                return

            # Step 2: Validate
            self._update_progress(
                f"Validating {len(pdf_files)} PDF files..."
            )
            observer.total = len(pdf_files)
            observer.counter = 0

            validated = self.finder.validate_pdfs(
                pdf_files,
                page_filter=page_filter,
                size_filter=size_filter,
                detect_duplicates=detect,
                callback=observer,
            )

            if self.operation_cancelled:
                self._finish_search()
                return

            # Step 3: Detect duplicates
            if detect:
                self._update_progress("Detecting duplicates...")
                validated = self.finder.detect_duplicates(validated)

            # Sort by size descending (default)
            validated.sort(key=lambda e: e.size, reverse=True)

            # Update UI
            self.root.after(0, lambda: self._on_search_complete(validated))

        except Exception as e:
            logging.exception("Search error")
            error_msg = str(e)
            self.root.after(
                0,
                lambda msg=error_msg: messagebox.showerror(
                    "Search Error", f"An error occurred: {msg}"
                ),
            )
            self._finish_search()

    def _on_search_complete(self, validated: list) -> None:
        self._populate_tree(validated)
        self.lbl_progress.config(
            text=f"Search complete. {len(validated)} PDFs found."
        )
        self._reset_progress()
        self._set_ui_busy(False)

    def _finish_search(self) -> None:
        self.root.after(0, self._finish_search_ui)

    def _finish_search_ui(self) -> None:
        self._reset_progress()
        self._set_ui_busy(False)

    # ------------------------------------------------------------------
    # Copy operation
    # ------------------------------------------------------------------

    def on_copy_selected(self) -> None:
        if self.ui_busy:
            return

        selected = self._get_selected_entries()
        if not selected:
            messagebox.showinfo(
                "No Selection", "Please select files to copy.", icon=INFO
            )
            return

        destination = self.cmb_destination.get().strip()
        if destination and not os.path.isdir(destination):
            messagebox.showerror(
                "Invalid Folder",
                f"Destination folder not found: {destination}",
                icon="error",
            )
            return

        if not destination:
            destination = filedialog.askdirectory(title="Select Destination Folder")
        if not destination:
            return

        # Save destination
        self.cmb_destination.set(destination)
        self.settings.add_frequent_destination(destination)
        self._refresh_frequent_destinations()

        # Filter out duplicates — copy only unique files
        files_to_copy = [e for e in selected if not e.is_duplicate]
        duplicate_count = len(selected) - len(files_to_copy)

        if not files_to_copy:
            messagebox.showinfo(
                "No Files to Copy",
                "All selected files are marked as duplicates.",
                icon=INFO,
            )
            return

        if duplicate_count > 0:
            self.lbl_progress.config(
                text=f"{duplicate_count} duplicate(s) will be skipped."
            )

        self.progressbar.config(mode=INDETERMINATE)
        self.progressbar.start(10)
        self.lbl_progress.config(text="Copying files...")
        self._set_ui_busy(True)
        self.operation_cancelled = False

        observer = OperationObserver(self)
        observer.total = len(files_to_copy)
        observer.counter = 0
        self.current_observer = observer

        self.operation_thread = threading.Thread(
            target=self._run_copy,
            args=(files_to_copy, destination, observer),
            daemon=True,
        )
        self.operation_thread.start()

    def _run_copy(
        self,
        files: list,
        destination: str,
        observer: "OperationObserver",
    ) -> None:
        try:
            copied = self.finder.copy_files(
                files, destination, callback=observer
            )

            if self.operation_cancelled:
                self.root.after(
                    0,
                    lambda: self.lbl_progress.config(
                        text="Copy cancelled."
                    ),
                )
            else:
                self.root.after(
                    0,
                    lambda copied_count=len(copied): messagebox.showinfo(
                        "Copy Complete",
                        f"Successfully copied {copied_count} file(s).",
                    ),
                )
        except Exception as e:
            logging.exception("Copy error")
            error_msg = str(e)
            self.root.after(
                0,
                lambda msg=error_msg: messagebox.showerror(
                    "Copy Error", f"An error occurred: {msg}"
                ),
            )
        finally:
            self._finish_copy()

    def _finish_copy(self) -> None:
        self.root.after(0, self._finish_copy_ui)

    def _finish_copy_ui(self) -> None:
        self._reset_progress()
        self._set_ui_busy(False)

    def _reset_progress(self) -> None:
        self.progressbar.stop()
        self.progressbar.config(mode=INDETERMINATE, value=0)

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    def on_export_csv(self) -> None:
        # Export all entries currently displayed (respecting search filter)
        items = list(self.visible_entry_ids)

        if not items:
            messagebox.showinfo(
                "No Data", "No PDFs to export.", icon=INFO
            )
            return

        output = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export to CSV",
        )
        if not output:
            return

        try:
            # Build entries from displayed items
            entries = []
            displayed_ids = set(items)
            for entry in self.all_entries:
                if entry.fullname in displayed_ids:
                    entries.append(entry)

            self.finder.save_to_csv(entries, output)
            messagebox.showinfo("Export Complete", f"Exported {len(entries)} entries to {output}.")
        except Exception as e:
            messagebox.showerror(
                "Export Error", f"Failed to export: {e}"
            )

    # ------------------------------------------------------------------
    # Progress helpers (thread-safe via root.after)
    # ------------------------------------------------------------------

    def _update_progress(self, message: str) -> None:
        self.root.after(0, lambda: self.lbl_progress.config(text=message))


class OperationObserver(CallBack):
    """Observer that updates the GUI via root.after for thread safety."""

    def __init__(self, app: PDFCrawler) -> None:
        super().__init__()
        self.app = app
        self.counter = 0
        self.total = 0

    def update(self, type: int, message: str) -> None:
        if self.is_cancelled():
            return

        self.counter += 1
        self.app.root.after(
            0,
            lambda m=message, c=self.counter, t=self.total: self._update_ui(m, c, t),
        )

    def _update_ui(self, message: str, count: int, total: int) -> None:
        if self.app.operation_cancelled:
            return

        if total > 0:
            max_value = total
            value = count if count <= total else total
            self.app.lbl_progress.config(text=f"{message} ({count}/{total})")
            self.app.progressbar.config(
                mode="determinate",
                maximum=max_value,
                value=value,
            )
        else:
            self.app.lbl_progress.config(text=message)


if __name__ == "__main__":
    root = tkb.Window("PDFCrawler")
    app = PDFCrawler(root)
    root.mainloop()
