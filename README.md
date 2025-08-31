# 🗂️ Fylax - Smart File Organization Utility

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform Support](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com/JohnTocci/Fylax)

**Fylax** is an intelligent file organization tool that automatically sorts your files into structured folders based on customizable rules. Whether you're dealing with a cluttered Downloads folder or organizing years of documents, Fylax makes file management effortless with its intuitive GUI and powerful automation features.

![Fylax Demo](https://via.placeholder.com/800x400/4CAF50/white?text=Fylax+Interface+Demo)

## ✨ Key Features

### 🎯 **Smart Organization**
- **Extension-based Rules**: Automatically sort files by type (.pdf → Documents/PDFs)
- **Advanced Pattern Matching**: Organize by filename patterns (invoice_*.pdf → Invoices)
- **Date-based Sorting**: Archive old files by date (files older than 1 year → Archive/2023/March)
- **Size-based Filtering**: Handle large files differently (files > 1GB → Large Files)

### 🔍 **Enhanced Preview & Control**
- **Interactive Dry-Run**: Preview all changes before applying them
- **Selective Organization**: Choose exactly which files to move/copy
- **Tree View**: Visual representation of proposed file structure
- **One-Click Undo**: Safely revert any organization operation

### 🔧 **Powerful Management**
- **Profile System**: Multiple rule sets for different scenarios (Work, Personal, etc.)
- **Duplicate Detection**: Find and handle duplicate files intelligently
- **Drag & Drop**: Simply drag folders onto the app to select them
- **Cross-Platform**: Works seamlessly on Windows, macOS, and Linux

### 🛡️ **Safety First**
- **Protected Files**: Automatically skips system and application files
- **Conflict Resolution**: Smart handling of naming conflicts
- **Operation Logging**: Complete audit trail of all file operations
- **Backup Integration**: Safe organization with full rollback capability

---

## 🚀 Quick Start

### 📦 Installation

#### Option 1: Using pip (Recommended)
```bash
pip install fylax
fylax
```

#### Option 2: From Source
```bash
# Clone the repository
git clone https://github.com/JohnTocci/Fylax.git
cd Fylax

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/gui.py
```

#### Option 3: Windows Executable
Download the latest `.exe` file from the [Releases](https://github.com/JohnTocci/Fylax/releases) page and run directly.

### 🎮 Basic Usage

1. **Launch Fylax** using one of the methods above
2. **Select a folder** to organize (or drag & drop it onto the app)
3. **Choose your settings**:
   - Enable dry-run mode to preview changes
   - Select move or copy operation
   - Choose whether to include subfolders
4. **Click "Organize"** and watch your files get sorted!

---

## ⚙️ Configuration

Fylax uses a `config.json` file to define organization rules. You can edit this file directly or use the built-in GUI editor.

### 📁 Basic Rules (Extension-based)

Perfect for simple file type organization:

```json
{
  "rules": {
    ".pdf": "Documents/PDFs",
    ".jpg": "Images/Photos", 
    ".jpeg": "Images/Photos",
    ".png": "Images/Screenshots",
    ".mp4": "Videos",
    ".mp3": "Audio/Music",
    ".zip": "Archives",
    ".exe": "Software"
  }
}
```

### 🎯 Advanced Rules

For more sophisticated organization needs:

```json
{
  "advanced_rules": [
    {
      "type": "filename_pattern",
      "pattern": "invoice_*.pdf",
      "destination": "Business/Invoices"
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

### 📋 Rule Types Reference

| Rule Type | Description | Example |
|-----------|-------------|---------|
| `filename_pattern` | Match files by name pattern | `screenshot_*.png` |
| `date` | Organize by file age | Files older than 1 year |
| `size` | Sort by file size | Files larger than 100MB |
| `extension` | Basic file type sorting | `.pdf` → Documents |

### 🎭 Profile System

Create different rule sets for different scenarios:

```json
{
  "active_profile": "work",
  "profiles": {
    "work": {
      "rules": {
        ".pdf": "Work/Documents",
        ".xlsx": "Work/Spreadsheets"
      }
    },
    "personal": {
      "rules": {
        ".jpg": "Personal/Photos",
        ".mp3": "Personal/Music"
      }
    }
  }
}
```

---

## 🖼️ Screenshots

### Main Interface
![Main Interface](https://via.placeholder.com/600x400/2196F3/white?text=Main+Organization+Interface)

### Dry-Run Preview
![Preview Dialog](https://via.placeholder.com/600x400/FF9800/white?text=Interactive+Preview+Dialog)

### Duplicate Detection
![Duplicate Scanner](https://via.placeholder.com/600x400/9C27B0/white?text=Duplicate+File+Detection)

---

## 🔧 Advanced Usage

### 📦 Building Executables

Create a standalone Windows executable:

```bash
# Install PyInstaller
pip install pyinstaller

# Build single-file executable
pyinstaller --noconfirm --windowed --onefile \
  --name Fylax \
  --icon assets/app.ico \
  --add-data "assets;assets" \
  src/gui.py
```

The executable will be created in the `dist/` folder.

### 🐍 Python API

Use Fylax programmatically in your own scripts:

```python
from src.main import organize_folder

# Organize a folder with custom settings
result = organize_folder(
    folder_path="/path/to/messy/folder",
    profile_name="default",
    mode="move",           # or "copy"
    dry_run=False,
    include_subfolders=True,
    unknown_destination="Misc"
)

print(f"Organized {result['moved']} files")
```

### 🔍 Duplicate File Management

```python
from src.main import find_duplicate_files, handle_duplicates

# Find duplicates
duplicates = find_duplicate_files(
    folder_path="/path/to/folder",
    min_size_mb=1  # Skip files smaller than 1MB
)

# Handle duplicates automatically
handle_duplicates(
    duplicates,
    action="move",         # "move", "delete", or "skip"
    destination="Duplicates",
    keep_criteria="shortest_path"  # or "longest_path", "first_found"
)
```

---

## 🔒 Safety & Security

Fylax is designed with safety as a top priority:

- **Protected Extensions**: Automatically skips system files (`.exe`, `.dll`, `.sys`, etc.)
- **Dangerous Path Detection**: Blocks organization of system directories
- **Hidden File Handling**: Respects hidden file attributes across platforms
- **Operation Logging**: Complete audit trail for all file operations
- **Undo Functionality**: One-click rollback for recent operations

### 🚫 Protected File Types

The following file types are never moved to prevent system damage:
- Executables: `.exe`, `.dll`, `.sys`, `.msi`
- System files: `.ini`, `.lnk`, `.bat`, `.cmd`
- Application bundles: `.app`, `.msix`, `.appx`

---

## 🛠️ Development

### 🏗️ Setup Development Environment

```bash
# Clone repository
git clone https://github.com/JohnTocci/Fylax.git
cd Fylax

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements.txt
pip install -e .

# Run in development mode
python src/gui.py
```

### 🧪 Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src
```

### 📝 Code Style

This project uses:
- **Black** for code formatting
- **isort** for import sorting  
- **flake8** for linting
- **mypy** for type checking

```bash
# Format code
black src/
isort src/

# Check style
flake8 src/
mypy src/
```

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### 🐛 Bug Reports

Found a bug? Please [open an issue](https://github.com/JohnTocci/Fylax/issues) with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- System information (OS, Python version)

### 💡 Feature Requests

Have an idea? We'd love to hear it! [Create a feature request](https://github.com/JohnTocci/Fylax/issues) with:
- Clear description of the feature
- Use case and benefits
- Proposed implementation (if any)

---

## 🔧 Troubleshooting

### Common Issues

**Q: Error about `customtkinter` not found**
```bash
pip install customtkinter>=5.2.2
```

**Q: GUI looks odd on high-DPI screens**
- Try switching Appearance to "System" or "Light" in the app settings

**Q: Files not organizing as expected**
- Check your rules in `config.json` for syntax errors
- Ensure destination folders don't conflict with source folders
- Enable dry-run mode to preview the organization

**Q: Application won't start**
- Ensure Python 3.8+ is installed
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check for error messages in the console

### 📞 Getting Help

- 📖 Check our [Wiki](https://github.com/JohnTocci/Fylax/wiki) for detailed guides
- 💬 [Open a discussion](https://github.com/JohnTocci/Fylax/discussions) for questions
- 🐛 [Report bugs](https://github.com/JohnTocci/Fylax/issues) for technical issues

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**John Tocci**
- 🌐 Website: [johntocci.com](https://johntocci.com)
- 📧 Email: [john@johntocci.com](mailto:john@johntocci.com)
- 🐙 GitHub: [@JohnTocci](https://github.com/JohnTocci)

---

## 🙏 Acknowledgments

- Thanks to all contributors who have helped improve Fylax
- Built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for the modern GUI
- Icons provided by the community

---

⭐ **If you find Fylax helpful, please consider giving it a star on GitHub!**

[🔝 Back to top](#-fylax---smart-file-organization-utility)