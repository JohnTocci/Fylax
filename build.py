#!/usr/bin/env python3
"""
Build script for Fylax
Creates Windows executable using PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🔨 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Main build function."""
    print("🚀 Building Fylax executable...")
    
    # Check if we're in the right directory
    if not Path("fylax/gui.py").exists():
        print("❌ Error: Must run from project root directory")
        sys.exit(1)
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("📦 Installing PyInstaller...")
        if not run_command("pip install pyinstaller", "PyInstaller installation"):
            sys.exit(1)
    
    # Clean previous builds
    if Path("dist").exists():
        print("🧹 Cleaning previous build...")
        shutil.rmtree("dist")
    if Path("build").exists():
        shutil.rmtree("build")
    
    # Build command
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--windowed", 
        "--onefile",
        "--name", "Fylax",
        "--icon", "assets/app.ico",
        "--add-data", "assets;assets" if os.name == 'nt' else "assets:assets",
        "src/fylax/gui.py"
    ]
    
    build_cmd = " ".join(cmd)
    
    if run_command(build_cmd, "Building executable"):
        print("\n🎉 Build completed successfully!")
        if os.name == 'nt':
            print(f"📁 Executable location: {Path('dist/Fylax.exe').absolute()}")
        else:
            print(f"📁 Executable location: {Path('dist/Fylax').absolute()}")
    else:
        print("\n💥 Build failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()