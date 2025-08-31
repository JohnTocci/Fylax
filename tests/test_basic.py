"""
Basic tests for Fylax file organization utility.
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_import_main():
    """Test that the main module can be imported."""
    try:
        import main
        assert hasattr(main, 'organize_folder')
        assert hasattr(main, 'get_profile_data')
    except ImportError as e:
        assert False, f"Failed to import main module: {e}"

def test_config_json_exists():
    """Test that config.json exists and is valid JSON."""
    config_path = Path(__file__).parent.parent / "config.json"
    assert config_path.exists(), "config.json file not found"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    assert "profiles" in config, "config.json missing profiles section"
    assert "active_profile" in config, "config.json missing active_profile"

def test_assets_directory():
    """Test that assets directory exists with required files."""
    assets_path = Path(__file__).parent.parent / "assets"
    assert assets_path.exists(), "assets directory not found"
    
    # Check for icon files
    ico_path = assets_path / "app.ico"
    png_path = assets_path / "app.png"
    
    # At least one icon should exist
    assert ico_path.exists() or png_path.exists(), "No app icon found in assets"

def test_readme_exists():
    """Test that README.md exists and has content."""
    readme_path = Path(__file__).parent.parent / "README.md"
    assert readme_path.exists(), "README.md not found"
    
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    assert len(content) > 100, "README.md appears to be too short"
    assert "Fylax" in content, "README.md should mention Fylax"

def test_requirements_file():
    """Test that requirements.txt exists and has customtkinter."""
    req_path = Path(__file__).parent.parent / "requirements.txt"
    assert req_path.exists(), "requirements.txt not found"
    
    with open(req_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    assert "customtkinter" in content, "requirements.txt should include customtkinter"

if __name__ == "__main__":
    test_import_main()
    test_config_json_exists()
    test_assets_directory()
    test_readme_exists()
    test_requirements_file()
    print("All basic tests passed!")