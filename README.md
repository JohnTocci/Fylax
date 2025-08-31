# Fylax
# A smart file organization utility
# Author: John Tocci

A simple utility to organize files in a chosen folder into subfolders based on file extensions defined in `config.json`.

## Quick start

1) Install dependencies (Windows PowerShell):

```
pip install -r requirements.txt
```

2) Run the GUI:

```
python .\src\gui.py
```

3) Select a folder and click Organize. Progress and results will stream in the log.
	- **Enhanced Dry-Run Preview**: When dry-run mode is enabled, Fylax shows an interactive preview with a tree view of proposed file movements, allowing you to select/deselect specific files before proceeding.
	- **Drag & Drop**: Drag folders from your file explorer and drop them onto the application to select them quickly.
	- **Undo Functionality**: Use "Undo Last Operation" to safely revert file movements and copies.
	- **Profiles**: Switch between different rule configurations in the Settings tab for different organization scenarios.
	- **Duplicate Detection**: Use the Duplicates tab to find and handle duplicate files with content-based detection.
	- Appearance menu switches Light/Dark/System.
	- Options let you include subfolders, dry-run, choose move/copy, and set a catch-all folder.
	- Theme changes apply immediately; if a run is active, they apply once it finishes.

## App icon

Place an icon file in `assets/` and it will be picked up automatically on startup:

- `assets/app.ico` (Windows)
- `assets/app.png` (macOS/Linux optional)

## Packaging (optional)

Create a single-file Windows executable with the app icon using PyInstaller. Run these in PowerShell from the project root, preferably with your virtual environment's Python:

```
pip install pyinstaller
pyinstaller --noconfirm ^
  --windowed ^
  --name Fylax ^
  --icon assets/app.ico ^
  --add-data "assets;assets" ^
  src/gui.py
```

Notes:
- `--windowed` prevents a console window.
- `--icon assets/app.ico` sets the executable’s icon.
- `--add-data "assets;assets"` bundles the assets folder; on macOS/Linux use `assets:assets`.
- After build, the app is in `dist/Fylax/` (folder) or `dist/Fylax.exe` if using `--onefile`.

To build a single-file exe add `--onefile`:

```
pyinstaller --noconfirm --windowed --onefile --name Fylax --icon assets/app.ico --add-data "assets;assets" src/gui.py
```

## Configure rules

Fylax supports both traditional extension-based rules and advanced pattern-based rules.

### Basic Rules (Extension-based)

Edit the `rules` section in `config.json`:

```json
{
  "rules": {
    ".pdf": "Documents/PDFs",
    ".jpg": "Images/Photos",
    ".mp4": "Videos"
  }
}
```

### Advanced Rules

Fylax supports advanced organization rules for more sophisticated file management:

```json
{
  "rules": { "...": "..." },
  "advanced_rules": [
    {
      "type": "filename_pattern",
      "pattern": "invoice_*.pdf",
      "destination": "Invoices"
    },
    {
      "type": "filename_pattern",
      "pattern": "vacation_2024_*",
      "destination": "Photos/Vacation 2024"
    },
    {
      "type": "date",
      "condition": "older_than_days",
      "value": 365,
      "destination": "Archive/{{year}}/{{month}}"
    },
    {
      "type": "size",
      "condition": "larger_than_mb",
      "value": 1024,
      "destination": "Large Files"
    }
  ]
}
```

#### Rule Types

**Filename Pattern Rules:**
- `pattern`: Wildcard pattern (* and ?) or regex if `use_regex: true`
- Matches files based on filename patterns

**Date Rules:**
- `condition`: `older_than_days`, `newer_than_days`, or `between_days`
- `value`: Number of days (or [min, max] for between_days)
- Supports template variables: `{{year}}`, `{{month}}`, `{{month_num}}`, `{{day}}`

**Size Rules:**
- `condition`: `larger_than_mb`, `smaller_than_mb`, `larger_than_kb`, `smaller_than_kb`, `between_mb`
- `value`: Size threshold in MB/KB (or [min, max] for between)

Advanced rules take priority over extension-based rules when they match.

Subfolders will be created inside the folder you choose when organizing.

## User Experience Features

### Enhanced Dry-Run Preview
When dry-run mode is enabled, Fylax displays an interactive preview dialog showing:
- Tree view of all files and their proposed destinations
- Ability to select/deselect individual files for organization
- Summary of what will be moved, copied, or skipped
- "Proceed with Selected" option to execute only chosen operations

### Undo Functionality
- **Operation Logging**: All file movements and copies are logged automatically
- **One-Click Undo**: "Undo Last Operation" button safely reverts the most recent organization
- **Batch Support**: Undoes entire organization sessions, not just individual files
- **Conflict Resolution**: Handles cases where original locations are occupied

### Profile System
- **Multiple Configurations**: Save different rule sets for various scenarios (Work, Personal, etc.)
- **Quick Switching**: Change active profiles from the Settings tab
- **Rule Isolation**: Each profile maintains its own set of traditional and advanced rules
- **Import/Export Ready**: Profiles are stored in a structured format for easy sharing

### Drag & Drop Support
- **Folder Selection**: Drag folders from file explorer directly onto the application
- **Visual Feedback**: Clear indication of drop zones and selected folders
- **Cross-Platform**: Works on Windows, macOS, and Linux

### Duplicate File Detection
- **Content-Based Detection**: Uses MD5 hashing to identify files with identical content
- **Smart Scanning**: Groups files by size first for efficient detection
- **Flexible Handling**: Options to move duplicates to a folder, delete them, or skip
- **Keep Criteria**: Choose which file to keep (first found, shortest path, longest path)
- **Size Filtering**: Set minimum file size to avoid scanning tiny files
- **Progress Tracking**: Real-time progress updates during scanning
- **Detailed Results**: Shows duplicate groups with file sizes and locations

## Advanced options (engine)

The organizing function accepts options (exposed in the GUI):

- include_subfolders: process files in nested folders
- mode: 'move' or 'copy'
- dry_run: simulate without changing files
- unknown_destination: folder name to use for unmatched extensions

The summary reports moved/copied/skipped/errors and simulations when dry-run is enabled.

## Troubleshooting

- If you see an error about `customtkinter` not found, install it:

```
pip install customtkinter
```

- If the window looks odd on high-DPI screens, try switching Appearance to System or Light.

