"""
Fylax - Smart File Organization Utility

A comprehensive file organization tool that automatically sorts files
into structured folders based on customizable rules.
"""

__version__ = "1.0.0"
__author__ = "John Tocci"
__email__ = "john@johntocci.com"

# Make main functions available at package level
from .main import organize_folder, get_profile_data, find_duplicate_files

__all__ = ["organize_folder", "get_profile_data", "find_duplicate_files"]