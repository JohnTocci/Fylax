"""
Fylax - Smart File Organization Utility
Author: John Tocci

GUI interface for the file organization utility.
"""

import os
import json
import threading
import queue
from typing import Dict, Optional, Tuple
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk
from tkinter import filedialog, messagebox

# Import engine (package-relative if run as module, else local)
try:
    from .main import organize_folder, undo_last_operation, get_available_profiles, get_active_profile_name, get_profile_data, save_profile, delete_profile, set_active_profile, find_duplicate_files, handle_duplicates
except Exception:  # pragma: no cover - fallback when run directly
    from main import organize_folder, undo_last_operation, get_available_profiles, get_active_profile_name, get_profile_data, save_profile, delete_profile, set_active_profile, find_duplicate_files, handle_duplicates  # type: ignore

APP_NAME = "Fylax"
APP_ID = "com.fylax.app"
ICON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.ico")


class EnhancedPreviewDialog:
    """Dialog for enhanced dry-run preview with file selection."""
    
    def __init__(self, parent, preview_results: Dict[str, list]):
        self.parent = parent
        self.preview_results = preview_results
        self.selected_files = set()  # Files selected for organization
        self.dialog = None
        self.result = False  # True if user chooses to proceed
        
    def show(self) -> bool:
        """Show the preview dialog and return True if user wants to proceed."""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("Organization Preview")
        self.dialog.geometry("800x600")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Make dialog modal
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        self._build_preview_ui()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (600 // 2)
        self.dialog.geometry(f"800x600+{x}+{y}")
        
        # Wait for dialog to close
        self.parent.wait_window(self.dialog)
        
        return self.result
        
    def _build_preview_ui(self):
        """Build the preview dialog UI."""
        self.dialog.grid_rowconfigure(1, weight=1)
        self.dialog.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkFrame(self.dialog)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(header, text="Organization Preview", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        
        # Summary
        would_moved = self.preview_results.get('would-moved', [])
        would_copied = self.preview_results.get('would-copied', [])
        skipped = self.preview_results.get('skipped', [])
        
        summary_text = f"Files to organize: {len(would_moved + would_copied)}, Skipped: {len(skipped)}"
        ctk.CTkLabel(header, text=summary_text).grid(row=0, column=1, sticky="e", padx=10, pady=10)
        
        # Tree view frame
        tree_frame = ctk.CTkFrame(self.dialog)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Create tree view with tkinter (customtkinter doesn't have treeview)
        style = ttk.Style()
        style.theme_use('clam')
        
        tree_container = tk.Frame(tree_frame, bg=tree_frame._fg_color[1])
        tree_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        self.tree = ttk.Treeview(tree_container, show="tree headings", selectmode="none")
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=v_scroll.set)
        
        h_scroll = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        h_scroll.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=h_scroll.set)
        
        # Configure tree columns
        self.tree["columns"] = ("action", "destination")
        self.tree.column("#0", width=300, minwidth=200)
        self.tree.column("action", width=100, minwidth=80)
        self.tree.column("destination", width=300, minwidth=200)
        
        self.tree.heading("#0", text="File")
        self.tree.heading("action", text="Action")
        self.tree.heading("destination", text="Destination")
        
        self._populate_tree()
        
        # Control buttons
        button_frame = ctk.CTkFrame(self.dialog)
        button_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        button_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkButton(button_frame, text="Select All", width=100, command=self._select_all).grid(row=0, column=0, padx=(10, 5), pady=10)
        ctk.CTkButton(button_frame, text="Select None", width=100, command=self._select_none).grid(row=0, column=1, padx=5, pady=10)
        
        ctk.CTkButton(button_frame, text="Cancel", width=100, command=self._on_cancel).grid(row=0, column=2, padx=(5, 10), pady=10)
        ctk.CTkButton(button_frame, text="Proceed with Selected", width=160, command=self._on_proceed).grid(row=0, column=3, padx=(5, 10), pady=10)
        
    def _populate_tree(self):
        """Populate the tree view with preview data."""
        # Group files by destination folder
        destinations = {}
        
        for file, dest in self.preview_results.get('would-moved', []):
            if dest not in destinations:
                destinations[dest] = {'moved': [], 'copied': []}
            destinations[dest]['moved'].append(file)
            
        for file, dest in self.preview_results.get('would-copied', []):
            if dest not in destinations:
                destinations[dest] = {'moved': [], 'copied': []}
            destinations[dest]['copied'].append(file)
        
        # Add skipped files
        if self.preview_results.get('skipped'):
            destinations['[SKIPPED]'] = {'moved': [], 'copied': [], 'skipped': []}
            for file, _ in self.preview_results.get('skipped', []):
                destinations['[SKIPPED]']['skipped'] = destinations['[SKIPPED]'].get('skipped', [])
                destinations['[SKIPPED]']['skipped'].append(file)
        
        # Populate tree
        for dest_folder, actions in sorted(destinations.items()):
            if dest_folder == '[SKIPPED]':
                folder_node = self.tree.insert("", "end", text=dest_folder, values=("", ""), open=True)
                for file in sorted(actions.get('skipped', [])):
                    self.tree.insert(folder_node, "end", text=f"📄 {file}", values=("skipped", ""), tags=("skipped",))
            else:
                folder_node = self.tree.insert("", "end", text=f"📁 {dest_folder}", values=("", ""), open=True)
                
                for file in sorted(actions.get('moved', [])):
                    file_node = self.tree.insert(folder_node, "end", text=f"📄 {file}", 
                                                values=("move", dest_folder), tags=("file", "move"))
                    self.selected_files.add(file_node)  # Default to selected
                    
                for file in sorted(actions.get('copied', [])):
                    file_node = self.tree.insert(folder_node, "end", text=f"📄 {file}", 
                                                values=("copy", dest_folder), tags=("file", "copy"))
                    self.selected_files.add(file_node)  # Default to selected
        
        # Configure tags for styling
        self.tree.tag_configure("skipped", foreground="gray")
        
        # Bind click events for selection
        self.tree.bind("<Button-1>", self._on_tree_click)
        
        self._update_tree_display()
        
    def _on_tree_click(self, event):
        """Handle tree item clicks for selection."""
        item = self.tree.identify('item', event.x, event.y)
        if item and "file" in self.tree.item(item, "tags"):
            if item in self.selected_files:
                self.selected_files.remove(item)
            else:
                self.selected_files.add(item)
            self._update_tree_display()
            
    def _update_tree_display(self):
        """Update tree display to show selected/unselected state."""
        for item in self.tree.get_children():
            self._update_item_display(item)
            
    def _update_item_display(self, item):
        """Update display for a tree item and its children."""
        if "file" in self.tree.item(item, "tags"):
            # Update file item display
            text = self.tree.item(item, "text")
            if item in self.selected_files:
                if not text.startswith("✓ "):
                    text = "✓ " + text
                    self.tree.item(item, text=text)
            else:
                if text.startswith("✓ "):
                    text = text[2:]
                    self.tree.item(item, text=text)
                    
        # Update children
        for child in self.tree.get_children(item):
            self._update_item_display(child)
            
    def _select_all(self):
        """Select all files for organization."""
        for item in self.tree.get_children():
            self._select_item_recursive(item, True)
        self._update_tree_display()
        
    def _select_none(self):
        """Deselect all files."""
        self.selected_files.clear()
        self._update_tree_display()
        
    def _select_item_recursive(self, item, select: bool):
        """Recursively select/deselect items."""
        if "file" in self.tree.item(item, "tags"):
            if select:
                self.selected_files.add(item)
            else:
                self.selected_files.discard(item)
                
        for child in self.tree.get_children(item):
            self._select_item_recursive(child, select)
            
    def _on_proceed(self):
        """User chose to proceed with selected files."""
        if not self.selected_files:
            messagebox.showwarning("No Files Selected", "Please select at least one file to organize.")
            return
            
        # Store selected files for later use
        self.result = True
        self.dialog.destroy()
        
    def _on_cancel(self):
        """User cancelled the operation."""
        self.result = False
        self.dialog.destroy()
        
    def get_selected_files(self) -> set:
        """Get the set of selected file tree items."""
        return self.selected_files


class OrganizerApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self._enable_windows_dpi_awareness()
        self._set_windows_appusermodel_id(APP_ID)
        self._set_app_icon()

        self.title(APP_NAME)
        self.geometry("1020x720")
        self.minsize(960, 600)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self._init_fonts()

        # Worker + UI queue
        self._worker: Optional[threading.Thread] = None
        self._queue: "queue.Queue[Tuple[str, Optional[str], str, Optional[str]]]" = queue.Queue()

        # Vars
        self.path_var = ctk.StringVar(value=os.path.expanduser("~"))
        self.include_var = ctk.BooleanVar(value=True)
        self.dryrun_var = ctk.BooleanVar(value=True)
        self.skip_hidden_var = ctk.BooleanVar(value=True)
        self.preserve_tree_var = ctk.BooleanVar(value=False)
        self.mode_var = ctk.StringVar(value="move")
        self.unknown_var = ctk.StringVar(value="")
        self.min_age_var = ctk.IntVar(value=0)
        self.min_age_label_var = ctk.StringVar(value="0d")
        # Junk deletion
        self.delete_junk_var = ctk.BooleanVar(value=False)
        self.junk_age_var = ctk.IntVar(value=14)
        self.junk_age_label_var = ctk.StringVar(value="14d")
        
        # Profile management
        self.active_profile_var = ctk.StringVar(value=get_active_profile_name())
        
        # Duplicate detection
        self.duplicate_action_var = ctk.StringVar(value="move_to_folder")
        self.duplicate_folder_var = ctk.StringVar(value="Duplicates")
        self.duplicate_min_size_var = ctk.IntVar(value=1)  # 1 KB minimum
        self.duplicate_keep_var = ctk.StringVar(value="first")

        # Build UI
        self._build_ui()
        self.after(120, self._drain_queue_periodic)

    # ---------- Windows helpers ----------
    def _enable_windows_dpi_awareness(self) -> None:
        if os.name != 'nt':
            return
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    def _set_windows_appusermodel_id(self, app_id: str) -> None:
        if os.name != 'nt':
            return
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass

    def _set_app_icon(self) -> None:
        if os.path.exists(ICON_PATH):
            try:
                self.iconbitmap(ICON_PATH)
            except Exception:
                pass
        if os.name == 'nt' and os.path.exists(ICON_PATH):
            try:
                import ctypes
                LR_LOADFROMFILE = 0x0010
                IMAGE_ICON = 1
                big = ctypes.windll.user32.LoadImageW(0, ICON_PATH, IMAGE_ICON, 256, 256, LR_LOADFROMFILE)
                small = ctypes.windll.user32.LoadImageW(0, ICON_PATH, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                WM_SETICON = 0x0080
                GCL_HICON = -14
                GCL_HICONSM = -34
                hwnd = self.winfo_id()
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 1, big)
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 0, small)
                try:
                    ctypes.windll.user32.SetClassLongPtrW(hwnd, GCL_HICON, big)
                    ctypes.windll.user32.SetClassLongPtrW(hwnd, GCL_HICONSM, small)
                except Exception:
                    pass
            except Exception:
                pass

    # ---------- Fonts ----------
    def _init_fonts(self) -> None:
        self.font_title = ("Segoe UI", 20, "bold")
        self.font_heading = ("Segoe UI", 15, "bold")
        self.font_body = ("Segoe UI", 13)
        self.font_small = ("Segoe UI", 11)

    # ---------- Build UI ----------
    def _build_ui(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, corner_radius=0)
        top.grid(row=0, column=0, sticky="nsew")
        top.grid_rowconfigure(1, weight=1)
        top.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(top, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=APP_NAME, font=self.font_title).grid(row=0, column=0, sticky="w", padx=14, pady=10)
        ctk.CTkButton(header, text="About", width=80, command=self._open_about).grid(row=0, column=1, padx=12, pady=10)

        # Tabs
        tabs = ctk.CTkTabview(top)
        tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        for name in ("Organize", "Duplicates", "Rules", "Settings"):
            tabs.add(name)
        self.tabs = tabs

        # Organize tab
        self._build_tab_organize(tabs.tab("Organize"))
        self._build_tab_duplicates(tabs.tab("Duplicates"))
        self._build_tab_rules(tabs.tab("Rules"))
        self._build_tab_settings(tabs.tab("Settings"))

    def _build_tab_organize(self, root: ctk.CTkFrame) -> None:
        root.grid_rowconfigure(2, weight=1)
        root.grid_columnconfigure(0, weight=1)

        # 1) Choose folder
        row = ctk.CTkFrame(root, corner_radius=12)
        row.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 6))
        row.grid_columnconfigure(0, weight=1)
        
        # Add drag-and-drop label
        drop_frame = ctk.CTkFrame(row, fg_color="transparent")
        drop_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 0))
        ctk.CTkLabel(drop_frame, text="💡 Tip: Drag and drop a folder here, or use the Browse button", 
                    font=("Segoe UI", 10), text_color=("gray50", "gray60")).grid(row=0, column=0, sticky="w")
        
        self.path_entry = ctk.CTkEntry(row, textvariable=self.path_var, placeholder_text="Choose folder…",
                                      height=36, font=self.font_body)
        self.path_entry.grid(row=1, column=0, sticky="ew", padx=(10, 10), pady=(5, 10))
        ctk.CTkButton(row, text="Browse", width=110, command=self._choose_folder).grid(row=1, column=1, padx=(0, 10), pady=(5, 10))
        
        # Enable drag and drop
        self._setup_drag_drop()

        # 2) Options
        opt = ctk.CTkFrame(root, corner_radius=12)
        opt.grid(row=1, column=0, sticky="ew", padx=14, pady=6)
        for i in range(10):
            opt.grid_columnconfigure(i, weight=0)
        opt.grid_columnconfigure(5, weight=1)  # age slider stretches

        ctk.CTkLabel(opt, text="2) Options", font=self.font_heading).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 2), columnspan=10)
        ctk.CTkSwitch(opt, text="Include subfolders", variable=self.include_var).grid(row=1, column=0, padx=(14, 16), pady=(2, 8))
        ctk.CTkSwitch(opt, text="Dry run", variable=self.dryrun_var).grid(row=1, column=1, padx=(0, 16), pady=(2, 8))
        ctk.CTkSwitch(opt, text="Skip hidden", variable=self.skip_hidden_var).grid(row=1, column=2, padx=(0, 16), pady=(2, 8))
        ctk.CTkSwitch(opt, text="Preserve subfolder tree", variable=self.preserve_tree_var).grid(row=1, column=3, padx=(0, 16), pady=(2, 8))
        ctk.CTkSwitch(opt, text="Delete junk files", variable=self.delete_junk_var,
                      command=self._update_junk_controls).grid(row=1, column=4, padx=(0, 16), pady=(2, 8))

        ctk.CTkLabel(opt, text="Mode").grid(row=2, column=0, sticky="e", padx=(14, 8), pady=(2, 12))
        ctk.CTkSegmentedButton(opt, values=["move", "copy"], variable=self.mode_var).grid(row=2, column=1, sticky="w", padx=(0, 16), pady=(2, 12))
        ctk.CTkLabel(opt, text="Catch-all folder").grid(row=2, column=2, sticky="e", padx=(14, 8))
        ctk.CTkEntry(opt, textvariable=self.unknown_var, placeholder_text="e.g., Misc", width=160).grid(row=2, column=3, sticky="w", padx=(0, 16))

        ctk.CTkLabel(opt, text="Min age (days)").grid(row=2, column=4, sticky="e", padx=(14, 8))
        self.age_slider = ctk.CTkSlider(opt, from_=0, to=30, number_of_steps=30, command=self._on_age_changed)
        self.age_slider.set(self.min_age_var.get())
        self.age_slider.grid(row=2, column=5, sticky="ew", padx=(0, 12))
        ctk.CTkLabel(opt, textvariable=self.min_age_label_var).grid(row=2, column=6, sticky="w")

        ctk.CTkLabel(opt, text="Junk age (days)").grid(row=2, column=7, sticky="e", padx=(14, 8))
        self.junk_age_slider = ctk.CTkSlider(
            opt, from_=7, to=60, number_of_steps=53,
            command=lambda v: (self.junk_age_var.set(int(float(v))), self.junk_age_label_var.set(str(int(float(v))) + 'd')))
        self.junk_age_slider.set(self.junk_age_var.get())
        self.junk_age_slider.grid(row=2, column=8, sticky="ew", padx=(0, 12))
        ctk.CTkLabel(opt, textvariable=self.junk_age_label_var).grid(row=2, column=9, sticky="w")
        self._update_junk_controls()

        # 3) Run
        run = ctk.CTkFrame(root, corner_radius=12)
        run.grid(row=2, column=0, sticky="ew", padx=14, pady=6)
        run.grid_columnconfigure(0, weight=1)
        self.progress = ctk.CTkProgressBar(run)
        self.progress.set(0)
        self.progress.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 6), columnspan=3)
        self.progress_label = ctk.CTkLabel(run, text="Ready", font=self.font_small, text_color=("gray25", "gray70"))
        self.progress_label.grid(row=0, column=2, sticky="e", padx=14)
        ctk.CTkButton(run, text="Organize", width=140, height=38, command=self._on_organize_clicked).grid(row=1, column=0, sticky="w", padx=14, pady=(2, 10))
        ctk.CTkButton(run, text="Undo Last", width=120, height=38, command=self._on_undo_clicked).grid(row=1, column=1, padx=5, pady=(2, 10))
        ctk.CTkButton(run, text="Open Folder", width=120,
                      command=lambda: os.startfile(self.path_var.get()) if os.name == 'nt' and os.path.isdir(self.path_var.get()) else None).grid(row=1, column=2, sticky="e", padx=14, pady=(2, 10))

        # Console
        console = ctk.CTkFrame(root, corner_radius=12)
        console.grid(row=3, column=0, sticky="nsew", padx=14, pady=(6, 12))
        console.grid_rowconfigure(1, weight=1)
        console.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(console, text="Activity log", font=self.font_heading).grid(row=0, column=0, sticky="w", padx=14, pady=(8, 0))
        ctk.CTkButton(console, text="Clear log", width=100, command=self._clear_log).grid(row=0, column=1, padx=14, pady=(8, 0))
        self.log = ctk.CTkTextbox(console, height=200, font=("Consolas", 12))
        self.log.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
        self.log.insert("end", "Ready. Configure options and click Organize.\n")
        self.log.configure(state="disabled")

    def _build_tab_duplicates(self, root: ctk.CTkFrame) -> None:
        root.grid_rowconfigure(2, weight=1)
        root.grid_columnconfigure(0, weight=1)
        
        # 1) Folder selection (reuse from organize tab)
        folder_frame = ctk.CTkFrame(root, corner_radius=12)
        folder_frame.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 6))
        folder_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(folder_frame, text="1) Select folder to scan for duplicates", font=self.font_heading).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 2), columnspan=2)
        ctk.CTkEntry(folder_frame, textvariable=self.path_var, placeholder_text="Choose folder…",
                    height=36, font=self.font_body).grid(row=1, column=0, sticky="ew", padx=(14, 10), pady=(5, 10))
        ctk.CTkButton(folder_frame, text="Browse", width=110, command=self._choose_folder).grid(row=1, column=1, padx=(0, 14), pady=(5, 10))
        
        # 2) Duplicate detection options
        options_frame = ctk.CTkFrame(root, corner_radius=12)
        options_frame.grid(row=1, column=0, sticky="ew", padx=14, pady=6)
        options_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(options_frame, text="2) Duplicate Detection Options", font=self.font_heading).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 2), columnspan=4)
        
        # Action selection
        ctk.CTkLabel(options_frame, text="Action:").grid(row=1, column=0, sticky="w", padx=(14, 8), pady=8)
        action_menu = ctk.CTkOptionMenu(options_frame, 
                                       values=["move_to_folder", "delete", "skip"], 
                                       variable=self.duplicate_action_var,
                                       width=140)
        action_menu.grid(row=1, column=1, sticky="w", padx=(0, 16), pady=8)
        
        # Folder name for move action
        ctk.CTkLabel(options_frame, text="Duplicate folder:").grid(row=1, column=2, sticky="w", padx=(0, 8), pady=8)
        ctk.CTkEntry(options_frame, textvariable=self.duplicate_folder_var, width=120).grid(row=1, column=3, sticky="w", padx=(0, 14), pady=8)
        
        # Keep criteria
        ctk.CTkLabel(options_frame, text="Keep:").grid(row=2, column=0, sticky="w", padx=(14, 8), pady=8)
        keep_menu = ctk.CTkOptionMenu(options_frame,
                                     values=["first", "shortest_path", "largest_path"],
                                     variable=self.duplicate_keep_var,
                                     width=140)
        keep_menu.grid(row=2, column=1, sticky="w", padx=(0, 16), pady=8)
        
        # Minimum file size
        ctk.CTkLabel(options_frame, text="Min size (KB):").grid(row=2, column=2, sticky="w", padx=(0, 8), pady=8)
        size_entry = ctk.CTkEntry(options_frame, textvariable=self.duplicate_min_size_var, width=120)
        size_entry.grid(row=2, column=3, sticky="w", padx=(0, 14), pady=8)
        
        # 3) Scan and results
        results_frame = ctk.CTkFrame(root, corner_radius=12)
        results_frame.grid(row=2, column=0, sticky="nsew", padx=14, pady=(6, 12))
        results_frame.grid_rowconfigure(2, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        
        # Scan controls
        scan_controls = ctk.CTkFrame(results_frame)
        scan_controls.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        scan_controls.grid_columnconfigure(1, weight=1)
        
        ctk.CTkButton(scan_controls, text="Scan for Duplicates", width=140, height=38, command=self._scan_duplicates).grid(row=0, column=0, padx=(0, 10), pady=5)
        ctk.CTkButton(scan_controls, text="Handle Duplicates", width=140, height=38, command=self._handle_duplicates).grid(row=0, column=1, padx=10, pady=5)
        
        # Progress bar
        self.duplicate_progress = ctk.CTkProgressBar(results_frame)
        self.duplicate_progress.set(0)
        self.duplicate_progress.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        # Results log
        ctk.CTkLabel(results_frame, text="Duplicate Scan Results", font=self.font_heading).grid(row=2, column=0, sticky="w", padx=10, pady=(10, 0))
        self.duplicate_log = ctk.CTkTextbox(results_frame, height=200, font=("Consolas", 12))
        self.duplicate_log.grid(row=3, column=0, sticky="nsew", padx=10, pady=(5, 10))
        self.duplicate_log.insert("end", "Ready to scan for duplicates.\n")
        self.duplicate_log.configure(state="disabled")
        
        # Store for later use
        self.duplicate_results = {}

    def _build_tab_rules(self, root: ctk.CTkFrame) -> None:
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(root, text="File type rules (extension → destination)", font=self.font_heading).grid(row=0, column=0, sticky="w", padx=14, pady=10)
        body = ctk.CTkScrollableFrame(root, corner_radius=12)
        body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 8))
        body.grid_columnconfigure(0, weight=1)
        self.rules_body = body

        # Header row
        hdr = ctk.CTkFrame(body)
        hdr.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        for i in range(3):
            hdr.grid_columnconfigure(i, weight=1 if i == 1 else 0)
        ctk.CTkLabel(hdr, text="Extension", width=160).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(hdr, text="Destination (relative)").grid(row=0, column=1, sticky="w")
        ctk.CTkButton(hdr, text="Add rule", width=90, command=self._add_rule_row).grid(row=0, column=2, padx=6)

        self._load_rules_into_ui()

        # Footer
        foot = ctk.CTkFrame(root)
        foot.grid(row=2, column=0, sticky="ew", padx=14, pady=(8, 10))
        ctk.CTkButton(foot, text="Reload", command=self._load_rules_into_ui).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(foot, text="Save", command=self._save_rules_from_ui).grid(row=0, column=1)

    def _build_tab_settings(self, root: ctk.CTkFrame) -> None:
        root.grid_columnconfigure(1, weight=1)
        
        # Profiles section
        ctk.CTkLabel(root, text="Organization Profiles", font=self.font_heading).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 10), columnspan=2)
        
        profile_frame = ctk.CTkFrame(root, corner_radius=8)
        profile_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 10))
        profile_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(profile_frame, text="Active Profile:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.profile_dropdown = ctk.CTkOptionMenu(profile_frame, values=get_available_profiles(), 
                                                 variable=self.active_profile_var, 
                                                 command=self._on_profile_changed)
        self.profile_dropdown.grid(row=0, column=1, sticky="ew", padx=10, pady=10)
        
        button_frame = ctk.CTkFrame(profile_frame, fg_color="transparent")
        button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        
        ctk.CTkButton(button_frame, text="Save Current as New", width=140, command=self._save_profile_as_new).grid(row=0, column=0, padx=(0, 5))
        ctk.CTkButton(button_frame, text="Delete Profile", width=120, command=self._delete_current_profile).grid(row=0, column=1, padx=5)
        
        # Appearance section
        ctk.CTkLabel(root, text="Appearance", font=self.font_heading).grid(row=2, column=0, sticky="w", padx=14, pady=(20, 0))
        ctk.CTkOptionMenu(root, values=["System", "Light", "Dark"], command=lambda m: ctk.set_appearance_mode(m)).grid(row=2, column=1, sticky="w", padx=14, pady=(20, 0))
        ctk.CTkLabel(root, text="Accent", font=self.font_heading).grid(row=3, column=0, sticky="w", padx=14, pady=(10, 0))
        ctk.CTkOptionMenu(root, values=["blue", "dark-blue", "green"], command=lambda t: ctk.set_default_color_theme(t)).grid(row=3, column=1, sticky="w", padx=14, pady=(10, 0))
        ctk.CTkLabel(root, text="UI Scale", font=self.font_heading).grid(row=4, column=0, sticky="w", padx=14, pady=(10, 0))
        ctk.CTkSlider(root, from_=0.8, to=1.3, number_of_steps=10, command=lambda v: ctk.set_widget_scaling(float(v))).grid(row=4, column=1, sticky="ew", padx=14, pady=(10, 0))
        ctk.CTkLabel(root, text="Text size", font=self.font_heading).grid(row=5, column=0, sticky="w", padx=14, pady=(10, 0))
        ctk.CTkOptionMenu(root, values=["Small", "Normal", "Large"], command=self._apply_text_size).grid(row=5, column=1, sticky="w", padx=14, pady=(10, 0))

    # ---------- Rules helpers ----------
    def _config_path(self) -> str:
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

    def _load_rules_into_ui(self) -> None:
        # Clear
        for child in list(self.rules_body.winfo_children())[1:]:
            child.destroy()
        # Load active profile data
        try:
            profile_data = get_profile_data()
            rules: Dict[str, str] = profile_data.get('rules', {})
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile data:\n{e}")
            return
        # Populate
        r = 1
        for ext, dest in sorted(rules.items()):
            self._add_rule_row(ext, dest, row=r)
            r += 1

    def _add_rule_row(self, ext: str = "", dest: str = "", row: Optional[int] = None) -> None:
        if row is None:
            row = max(1, len(self.rules_body.winfo_children()))
        frame = ctk.CTkFrame(self.rules_body)
        frame.grid(row=row, column=0, sticky="ew", padx=8, pady=4)
        frame.grid_columnconfigure(1, weight=1)
        e = ctk.CTkEntry(frame, width=120)
        e.insert(0, ext)
        e.grid(row=0, column=0, padx=(6, 10), pady=4)
        d = ctk.CTkEntry(frame)
        d.insert(0, dest)
        d.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=4)
        ctk.CTkButton(frame, text="Delete", width=70, command=frame.destroy).grid(row=0, column=2, padx=4)

    def _save_rules_from_ui(self) -> None:
        new_rules: Dict[str, str] = {}
        for child in self.rules_body.winfo_children()[1:]:
            entries = [c for c in child.winfo_children() if isinstance(c, ctk.CTkEntry)]
            if len(entries) < 2:
                continue
            ext = entries[0].get().strip().lower()
            dest = entries[1].get().strip()
            if not ext:
                continue
            if not ext.startswith('.'):
                ext = '.' + ext
            if os.path.isabs(dest) or dest.startswith(('\\', '/')) or any(part in ('..', '') for part in dest.split(os.sep)):
                messagebox.showerror("Invalid destination", f"Destination must be a simple relative path: {dest}")
                return
            new_rules[ext] = dest
        
        # Get current active profile data and update rules
        try:
            current_profile_data = get_profile_data()
            current_profile_data['rules'] = new_rules
            
            # Save updated profile data
            active_profile_name = get_active_profile_name()
            if save_profile(active_profile_name, current_profile_data):
                messagebox.showinfo("Saved", f"Rules saved to profile '{active_profile_name}'")
            else:
                messagebox.showerror("Error", f"Failed to save rules to profile '{active_profile_name}'")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save rules: {e}")

    # ---------- Actions ----------
    def _choose_folder(self) -> None:
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)
            
    def _setup_drag_drop(self) -> None:
        """Set up drag and drop functionality for the main window."""
        try:
            # Try to enable drag and drop using tkinter dnd (basic support)
            # This works on Windows and some Linux distributions
            if hasattr(self, 'tk'):
                # Enable drag and drop events
                self.drop_target_register(tk.DND_FILES)
                self.dnd_bind('<<Drop>>', self._on_drop)
        except Exception:
            # If drag and drop isn't available, that's okay
            pass
            
        # Alternative: Bind to window drag events (works on most platforms)
        try:
            # Register for file drop events
            self.bind('<Button-1>', self._on_window_click)
            self.path_entry.bind('<Button-1>', self._on_path_entry_click)
            
            # For systems that support it, listen for drop events
            self.bind('<Drop>', self._on_drop)
            self.path_entry.bind('<Drop>', self._on_drop)
            
        except Exception:
            pass
            
    def _on_drop(self, event) -> None:
        """Handle file/folder drop events."""
        try:
            # Get dropped file paths
            if hasattr(event, 'data'):
                files = event.data.split()
            elif hasattr(event, 'widget') and hasattr(event.widget, 'selection_get'):
                try:
                    files = [event.widget.selection_get()]
                except Exception:
                    return
            else:
                return
                
            # Use the first dropped item if it's a directory
            for file_path in files:
                file_path = file_path.strip('{}')  # Remove braces if present
                if os.path.isdir(file_path):
                    self.path_var.set(file_path)
                    self._append_log(f"Folder selected via drag-and-drop: {file_path}")
                    break
                    
        except Exception as e:
            self._append_log(f"Drag-and-drop error: {e}")
            
    def _on_window_click(self, event) -> None:
        """Handle window click (for focus)."""
        pass
        
    def _on_path_entry_click(self, event) -> None:
        """Handle path entry click."""
        pass

    def _on_age_changed(self, v: float) -> None:
        self.min_age_var.set(int(float(v)))
        self.min_age_label_var.set(f"{self.min_age_var.get()}d")

    def _update_junk_controls(self) -> None:
        state = "normal" if self.delete_junk_var.get() else "disabled"
        try:
            self.junk_age_slider.configure(state=state)
        except Exception:
            pass

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.insert("end", "Log cleared.\n")
        self.log.configure(state="disabled")

    def _append_log(self, line: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _format_log_line(self, file: str, dest: Optional[str], status: str, info: Optional[str]) -> str:
        sym = {
            'moved': '➡',
            'copied': '⧉',
            'skipped': '⟳',
            'deleted': '🗑',
            'would-move': '…',
            'would-copy': '…',
            'would-delete': '⋯',
            'error': '✖',
        }.get(status, '•')
        if status == 'error' and info:
            return f"{sym} {file} (error - {info})"
        if dest:
            return f"{sym} {file} → {dest} ({status})"
        return f"{sym} {file} ({status}{' - ' + info if info else ''})"

    def _on_organize_clicked(self) -> None:
        path = self.path_var.get().strip()
        if not path or not os.path.isdir(path):
            messagebox.showerror("Invalid folder", "Please choose a valid folder.")
            return
        if self.delete_junk_var.get() and not self.dryrun_var.get():
            if not messagebox.askyesno("Confirm delete", "Junk deletion is enabled. This will permanently delete matching files older than the threshold. Continue?"):
                return
        if self._worker and self._worker.is_alive():
            messagebox.showinfo("Busy", "Please wait for the current operation to finish.")
            return
            
        # Enhanced preview for dry-run mode
        if self.dryrun_var.get():
            self._show_enhanced_preview()
        else:
            # Direct organization for non-dry-run
            self.progress.set(0)
            self.progress_label.configure(text="Working…")
            self._worker = threading.Thread(target=self._run_organize, daemon=True)
            self._worker.start()

    def _show_enhanced_preview(self) -> None:
        """Show enhanced preview dialog for dry-run."""
        # First run a quick dry-run to get preview data
        self.progress.set(0)
        self.progress_label.configure(text="Generating preview…")
        
        # Run dry-run in background thread
        self._preview_worker = threading.Thread(target=self._generate_preview, daemon=True)
        self._preview_worker.start()
        
    def _generate_preview(self) -> None:
        """Generate preview data in background thread."""
        try:
            # Get organize parameters
            path = self.path_var.get().strip()
            include = self.include_var.get()
            mode = self.mode_var.get()
            unknown = self.unknown_var.get().strip() or None
            preserve = self.preserve_tree_var.get()
            min_age = int(self.min_age_var.get()) if self.min_age_var.get() > 0 else None
            skip_hidden = self.skip_hidden_var.get()
            delete_junk = self.delete_junk_var.get()
            junk_age = int(self.junk_age_var.get()) if delete_junk else None
            
            # Run dry-run organize
            results = organize_folder(
                path,
                on_file_processed=None,  # No callback for preview
                include_subfolders=include,
                mode=mode,
                dry_run=True,
                unknown_destination=unknown,
                allow_dangerous=False,
                preserve_tree=preserve,
                min_age_days=min_age,
                skip_hidden=skip_hidden,
                delete_junk=delete_junk,
                junk_min_age_days=junk_age,
            )
            
            # Show preview dialog on main thread
            self.after(0, lambda: self._show_preview_dialog(results))
            
        except Exception as e:
            self.after(0, lambda: self._on_preview_error(str(e)))
            
    def _show_preview_dialog(self, results: Dict) -> None:
        """Show the preview dialog with results."""
        self.progress.set(0)
        self.progress_label.configure(text="Ready")
        
        if not any(results.get(key, []) for key in ['would-moved', 'would-copied']):
            messagebox.showinfo("Nothing to Organize", "No files found that match the current rules.")
            return
            
        # Show enhanced preview dialog
        preview_dialog = EnhancedPreviewDialog(self, results)
        if preview_dialog.show():
            # User chose to proceed - run actual organization
            messagebox.showinfo("Proceeding", "Starting organization with selected files...")
            self.dryrun_var.set(False)  # Temporarily disable dry-run
            self.progress.set(0)
            self.progress_label.configure(text="Working…")
            self._worker = threading.Thread(target=self._run_organize_final, daemon=True)
            self._worker.start()
        else:
            # User cancelled
            self._append_log("Organization cancelled by user")
            
    def _run_organize_final(self) -> None:
        """Run the final organization after preview confirmation."""
        try:
            self._run_organize()
        finally:
            # Re-enable dry-run mode
            self.after(0, lambda: self.dryrun_var.set(True))
            
    def _on_preview_error(self, error_msg: str) -> None:
        """Handle preview generation error."""
        self.progress.set(0)
        self.progress_label.configure(text="Ready")
        messagebox.showerror("Preview Error", f"Failed to generate preview: {error_msg}")
        self._append_log(f"Preview error: {error_msg}")

    def _on_undo_clicked(self) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showinfo("Busy", "Please wait for the current operation to finish.")
            return
            
        result = messagebox.askyesno("Confirm Undo", 
                                   "This will attempt to undo the last organization operation.\n"
                                   "Files will be moved back to their original locations.\n\n"
                                   "Continue?")
        if not result:
            return
            
        try:
            undo_result = undo_last_operation()
            
            # Display results
            messages = []
            if undo_result['reverted']:
                messages.extend(undo_result['reverted'])
            if undo_result['info']:
                messages.extend(undo_result['info'])
                
            if undo_result['errors']:
                error_msg = "Undo completed with errors:\n\n" + "\n".join(undo_result['errors'])
                if messages:
                    error_msg += "\n\nSuccessful operations:\n" + "\n".join(messages)
                messagebox.showerror("Undo Errors", error_msg)
            elif messages:
                messagebox.showinfo("Undo Complete", "\n".join(messages))
            else:
                messagebox.showinfo("Nothing to Undo", "No recent operations found to undo.")
                
            # Update log
            for msg in messages:
                self._append_log(f"UNDO: {msg}")
            for err in undo_result['errors']:
                self._append_log(f"UNDO ERROR: {err}")
                
        except Exception as e:
            messagebox.showerror("Undo Failed", f"Failed to undo operation: {e}")
            self._append_log(f"UNDO ERROR: {e}")

    def _run_organize(self) -> None:
        path = self.path_var.get().strip()
        include = self.include_var.get()
        mode = self.mode_var.get()
        dry = self.dryrun_var.get()
        unknown = self.unknown_var.get().strip() or None
        preserve = self.preserve_tree_var.get()
        min_age = int(self.min_age_var.get()) if self.min_age_var.get() > 0 else None
        skip_hidden = self.skip_hidden_var.get()
        delete_junk = self.delete_junk_var.get()
        junk_age = int(self.junk_age_var.get()) if delete_junk else None

        def callback(file: str, dest: Optional[str], status: str, info: Optional[str]) -> None:
            self._queue.put((file, dest, status, info))

        try:
            results = organize_folder(
                path,
                on_file_processed=callback,
                include_subfolders=include,
                mode=mode,
                dry_run=dry,
                unknown_destination=unknown,
                allow_dangerous=False,
                preserve_tree=preserve,
                min_age_days=min_age,
                skip_hidden=skip_hidden,
                delete_junk=delete_junk,
                junk_min_age_days=junk_age,
            )
        except Exception as e:
            self._queue.put(("", None, "error", str(e)))
            results = {}

        # Summary
        moved = len(results.get('moved', []))
        copied = len(results.get('copied', []))
        skipped = len(results.get('skipped', []))
        deleted = len(results.get('deleted', []))
        errs = len(results.get('errors', []))
        wm = len(results.get('would-moved', []))
        wc = len(results.get('would-copied', []))
        wd = len(results.get('would-deleted', []))
        summary = f"Done. moved={moved}, copied={copied}, deleted={deleted}, would-move={wm}, would-copy={wc}, would-delete={wd}, skipped={skipped}, errors={errs}"
        self._queue.put((summary, None, "summary", None))

    def _drain_queue_periodic(self) -> None:
        try:
            while True:
                file, dest, status, info = self._queue.get_nowait()
                if status == "summary":
                    self._append_log(file)
                    self.progress.set(1)
                    self.progress_label.configure(text="Done")
                    continue
                self._append_log(self._format_log_line(file, dest, status, info))
        except queue.Empty:
            pass
        self.after(120, self._drain_queue_periodic)

    def _apply_text_size(self, choice: str) -> None:
        if choice == "Small":
            self.font_title = ("Segoe UI", 18, "bold")
            self.font_heading = ("Segoe UI", 14, "bold")
            self.font_body = ("Segoe UI", 12)
            self.font_small = ("Segoe UI", 10)
        elif choice == "Large":
            self.font_title = ("Segoe UI", 22, "bold")
            self.font_heading = ("Segoe UI", 16, "bold")
            self.font_body = ("Segoe UI", 14)
            self.font_small = ("Segoe UI", 12)
        else:
            self._init_fonts()
        # Rebuild header texts that reference fonts (simple refresh)
        for w in self.winfo_children():
            w.destroy()
        self._build_ui()

    # ---------- Duplicate Detection Methods ----------
    def _scan_duplicates(self) -> None:
        """Scan for duplicate files in the selected folder."""
        path = self.path_var.get().strip()
        if not path or not os.path.isdir(path):
            messagebox.showerror("Invalid folder", "Please choose a valid folder.")
            return
            
        if self._worker and self._worker.is_alive():
            messagebox.showinfo("Busy", "Please wait for the current operation to finish.")
            return
            
        # Clear previous results
        self.duplicate_results = {}
        self.duplicate_progress.set(0)
        
        # Start scanning in background
        self._duplicate_worker = threading.Thread(target=self._run_duplicate_scan, daemon=True)
        self._duplicate_worker.start()
        
    def _run_duplicate_scan(self) -> None:
        """Run duplicate scan in background thread."""
        try:
            path = self.path_var.get().strip()
            min_size_kb = self.duplicate_min_size_var.get()
            min_size_bytes = max(1, min_size_kb * 1024)  # Convert KB to bytes
            
            # Progress callback
            def progress_callback(filename: str, processed: int, total: int):
                progress = processed / total if total > 0 else 0
                self.after(0, lambda: self.duplicate_progress.set(progress))
                self.after(0, lambda: self._append_duplicate_log(f"Scanning: {filename}"))
            
            self.after(0, lambda: self._append_duplicate_log("Starting duplicate scan..."))
            
            # Find duplicates
            duplicates = find_duplicate_files(
                path,
                include_subfolders=self.include_var.get(),
                skip_hidden=self.skip_hidden_var.get(),
                min_file_size=min_size_bytes,
                hash_algorithm='md5',
                on_progress=progress_callback
            )
            
            # Store results and update UI
            self.duplicate_results = duplicates
            self.after(0, lambda: self._display_duplicate_results(duplicates))
            
        except Exception as e:
            self.after(0, lambda: self._on_duplicate_scan_error(str(e)))
            
    def _display_duplicate_results(self, duplicates: Dict[str, List[Tuple[str, str]]]) -> None:
        """Display duplicate scan results."""
        self.duplicate_progress.set(1)
        
        if not duplicates:
            self._append_duplicate_log("No duplicates found!")
            return
            
        total_duplicates = sum(len(files) - 1 for files in duplicates.values())  # -1 because we keep one
        duplicate_groups = len(duplicates)
        
        self._append_duplicate_log(f"\nScan complete!")
        self._append_duplicate_log(f"Found {duplicate_groups} groups of duplicates")
        self._append_duplicate_log(f"Total duplicate files: {total_duplicates}")
        
        # Show details of each group
        for i, (file_hash, files) in enumerate(duplicates.items(), 1):
            self._append_duplicate_log(f"\nGroup {i} ({len(files)} files):")
            for full_path, relative_path in files:
                try:
                    file_size = os.path.getsize(full_path)
                    size_str = f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} MB"
                    self._append_duplicate_log(f"  • {relative_path} ({size_str})")
                except OSError:
                    self._append_duplicate_log(f"  • {relative_path} (size unknown)")
                
        self._append_duplicate_log(f"\nReady to handle duplicates. Click 'Handle Duplicates' to proceed.")
        
    def _handle_duplicates(self) -> None:
        """Handle detected duplicates according to user settings."""
        if not self.duplicate_results:
            messagebox.showwarning("No Duplicates", "Please scan for duplicates first.")
            return
            
        action = self.duplicate_action_var.get()
        if action == "delete":
            result = messagebox.askyesno("Confirm Delete", 
                                       "This will permanently delete duplicate files. "
                                       "Are you sure you want to proceed?")
            if not result:
                return
                
        # Start handling in background
        self._duplicate_worker = threading.Thread(target=self._run_handle_duplicates, daemon=True)
        self._duplicate_worker.start()
        
    def _run_handle_duplicates(self) -> None:
        """Handle duplicates in background thread."""
        try:
            action = self.duplicate_action_var.get()
            duplicate_folder = self.duplicate_folder_var.get()
            keep_criteria = self.duplicate_keep_var.get()
            
            def progress_callback(filename: str, dest: Optional[str], status: str, info: Optional[str]):
                log_msg = f"{status.upper()}: {filename}"
                if dest:
                    log_msg += f" -> {dest}"
                if info:
                    log_msg += f" ({info})"
                self.after(0, lambda: self._append_duplicate_log(log_msg))
            
            self.after(0, lambda: self._append_duplicate_log(f"\nHandling duplicates with action: {action}"))
            
            # Handle duplicates
            results = handle_duplicates(
                self.duplicate_results,
                action=action,
                duplicate_folder=duplicate_folder,
                keep_criteria=keep_criteria,
                dry_run=False,  # Always execute for now
                on_file_processed=progress_callback
            )
            
            # Show results
            self.after(0, lambda: self._show_duplicate_handle_results(results))
            
        except Exception as e:
            self.after(0, lambda: self._on_duplicate_handle_error(str(e)))
            
    def _show_duplicate_handle_results(self, results: Dict) -> None:
        """Show results of duplicate handling."""
        moved = len(results.get('moved', []))
        deleted = len(results.get('deleted', []))
        skipped = len(results.get('skipped', []))
        errors = len(results.get('errors', []))
        
        summary = f"\nDuplicate handling complete!"
        summary += f"\nMoved: {moved}, Deleted: {deleted}, Skipped: {skipped}, Errors: {errors}"
        
        self._append_duplicate_log(summary)
        
        if errors > 0:
            messagebox.showwarning("Completed with Errors", 
                                 f"Duplicate handling completed but encountered {errors} errors. "
                                 "Check the log for details.")
        else:
            messagebox.showinfo("Complete", "Duplicate handling completed successfully!")
            
    def _on_duplicate_scan_error(self, error_msg: str) -> None:
        """Handle duplicate scan error."""
        self.duplicate_progress.set(0)
        self._append_duplicate_log(f"Scan error: {error_msg}")
        messagebox.showerror("Scan Error", f"Failed to scan for duplicates: {error_msg}")
        
    def _on_duplicate_handle_error(self, error_msg: str) -> None:
        """Handle duplicate handling error."""
        self._append_duplicate_log(f"Handle error: {error_msg}")
        messagebox.showerror("Handle Error", f"Failed to handle duplicates: {error_msg}")
        
    def _append_duplicate_log(self, text: str) -> None:
        """Append text to duplicate log."""
        self.duplicate_log.configure(state="normal")
        self.duplicate_log.insert("end", text + "\n")
        self.duplicate_log.see("end")
        self.duplicate_log.configure(state="disabled")

    # ---------- Profile Management ----------
    def _on_profile_changed(self, profile_name: str) -> None:
        """Handle profile selection change."""
        if set_active_profile(profile_name):
            self.active_profile_var.set(profile_name)
            # Reload rules into the Rules tab
            self._load_rules_into_ui()
            messagebox.showinfo("Profile Changed", f"Switched to profile: {profile_name}")
        else:
            messagebox.showerror("Error", f"Failed to switch to profile: {profile_name}")
            # Revert dropdown to current active profile
            self.active_profile_var.set(get_active_profile_name())
    
    def _save_profile_as_new(self) -> None:
        """Save current rules as a new profile."""
        # Get profile name from user
        from tkinter import simpledialog
        profile_name = simpledialog.askstring("New Profile", "Enter profile name:")
        
        if not profile_name:
            return
            
        if profile_name in get_available_profiles():
            result = messagebox.askyesno("Profile Exists", 
                                       f"Profile '{profile_name}' already exists. Overwrite?")
            if not result:
                return
        
        # Get current profile data and save it with new name
        current_profile = get_profile_data()
        
        if save_profile(profile_name, current_profile):
            # Update dropdown
            self.profile_dropdown.configure(values=get_available_profiles())
            messagebox.showinfo("Profile Saved", f"Profile '{profile_name}' saved successfully.")
        else:
            messagebox.showerror("Error", f"Failed to save profile '{profile_name}'.")
    
    def _delete_current_profile(self) -> None:
        """Delete the currently selected profile."""
        current_profile = self.active_profile_var.get()
        
        if current_profile == "default":
            messagebox.showerror("Cannot Delete", "Cannot delete the default profile.")
            return
            
        if current_profile == get_active_profile_name():
            messagebox.showerror("Cannot Delete", "Cannot delete the currently active profile.")
            return
            
        result = messagebox.askyesno("Confirm Delete", 
                                   f"Are you sure you want to delete profile '{current_profile}'?\n"
                                   "This action cannot be undone.")
        if not result:
            return
            
        if delete_profile(current_profile):
            # Update dropdown and switch to default
            available_profiles = get_available_profiles()
            self.profile_dropdown.configure(values=available_profiles)
            if "default" in available_profiles:
                self.active_profile_var.set("default")
                set_active_profile("default")
                self._load_rules_into_ui()
            messagebox.showinfo("Profile Deleted", f"Profile '{current_profile}' deleted successfully.")
        else:
            messagebox.showerror("Error", f"Failed to delete profile '{current_profile}'.")

    def _open_about(self) -> None:
        messagebox.showinfo(
            "About",
            f"{APP_NAME}\n\nA smart file organization utility\nAuthor: John Tocci\n\nOrganize by rules (config.json). Move or copy with dry-run.\nSafe junk deletion with age gate. Windows DPI-aware.\n\n© 2025"
        )


def main() -> None:
    app = OrganizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
