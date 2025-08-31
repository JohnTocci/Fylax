"""
Fylax - Smart File Organization Utility
Author: John Tocci

Core organizing engine for file organization based on configurable rules.
Supports extension-based, pattern-based, date-based, and size-based organization.
"""

import os
import shutil
import json
import fnmatch
import re
import time
import hashlib
from collections import defaultdict
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple, Union, Any, Set

# ---- Never relocate these (expandable) ----
PROTECTED_EXTS = {
    '.exe', '.dll', '.sys', '.msi', '.mui', '.manifest', '.ocx',
    '.ini', '.lnk', '.bat', '.cmd', '.ps1', '.service',
    '.com', '.scr', '.cpl', '.drv', '.msix', '.appx', '.vbs', '.reg'
}

# ---- Junk detection (safe heuristics, expandable) ----
# Lowercase fnmatch patterns; applied to basenames only.
DEFAULT_JUNK_PATTERNS = [
    # Incomplete downloads / temp
    '*.crdownload', '*.part', '*.partial', '*.tmp', '~$*', '*~',
    # Installers (Windows)
    'setup*.exe', '*installer*.exe', '*update*.exe', '*patch*.exe', '*uninstall*.exe',
    'setup*.msi', '*installer*.msi', '*update*.msi', '*patch*.msi',
    # Archives often used for installers
    '*installer*.zip', '*setup*.zip', '*installer*.7z', '*setup*.7z',
    # Screenshots (common names)
    'screenshot*.png', 'screenshot*.jpg', 'screenshot*.jpeg',
    'screen shot*.png', 'screen shot*.jpg', 'screen shot*.jpeg',
    'snip*.png', 'snip*.jpg', 'snip*.jpeg',
]

# ---- Default directory exclusions when include_subfolders=True ----
DEFAULT_EXCLUDE_DIRS = {'node_modules', '.git', '__pycache__', 'venv', 'build', 'dist'}

def _get_config_path() -> str:
    """Absolute path to config.json relative to project root."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, 'config.json')

def _is_hidden(name: str, fullpath: Optional[str] = None) -> bool:
    """Treat dotfiles/known junk as hidden; on Windows also check file attributes when possible."""
    base = name if fullpath is None else os.path.basename(fullpath)
    if base.startswith('.') or base.lower() in {'thumbs.db', 'desktop.ini'}:
        return True
    if os.name == 'nt' and fullpath:
        try:
            import ctypes  # type: ignore
            FILE_ATTRIBUTE_HIDDEN = 0x2
            FILE_ATTRIBUTE_SYSTEM = 0x4
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(fullpath))
            if attrs != -1 and (attrs & (FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)):
                return True
        except Exception:
            pass
    return False

def _is_subpath(child: str, parent: str) -> bool:
    a, b = os.path.abspath(child), os.path.abspath(parent)
    try:
        return os.path.commonpath([a, b]) == os.path.abspath(parent)
    except Exception:
        return False

def _is_dangerous_folder(folder: str) -> bool:
    """Block drive root exactly, and block Windows/Program Files/AppData subtrees."""
    folder = os.path.abspath(folder)
    drive, _ = os.path.splitdrive(folder)

    # EXACT drive root only (e.g., C:\)
    if drive and folder.rstrip("\\/") == (drive + os.sep):
        return True

    # Subtree blocks
    roots = [
        os.environ.get('WINDIR', os.path.join(drive or 'C:', 'Windows')),
        os.environ.get('ProgramFiles', os.path.join(drive or 'C:', 'Program Files')),
        os.environ.get('ProgramFiles(x86)', os.path.join(drive or 'C:', 'Program Files (x86)')),
        os.path.join(os.path.expanduser('~'), 'AppData'),
    ]
    roots = [os.path.abspath(p) for p in roots if p]
    return any(_is_subpath(folder, r) for r in roots)

def _looks_like_app_dir(p: str) -> bool:
    """Heuristic: skip directories that look like app installs or build outputs."""
    try:
        names = os.listdir(p)
    except Exception:
        return False
    lower = {n.lower() for n in names}
    markers = {'bin', 'lib', 'resources', 'plugins', 'node_modules', 'dist', 'build', 'venv', '.git'}
    if markers & lower:
        return True
    exts = {os.path.splitext(n)[1].lower() for n in names}
    return ('.exe' in exts and ('.dll' in exts or '.manifest' in exts))

def _normalize_rules(raw: Dict[str, str]) -> Dict[str, str]:
    """Lowercase extension keys, trim values, ensure relative destination names."""
    rules: Dict[str, str] = {}
    for k, v in raw.items():
        ek = str(k).strip().lower()
        dest = str(v).strip()
        if not ek.startswith('.'):
            ek = '.' + ek  # tolerate 'jpg' in config
        # destination must be a simple relative path (no drive, no leading slash, no traversal)
        if os.path.isabs(dest) or dest.startswith(('/', '\\')) or any(part in ('..', '') for part in dest.split(os.sep)):
            raise ValueError(f"Invalid destination in config: {dest!r}")
        rules[ek] = dest
    return rules

def _ext_candidates(filename: str) -> List[str]:
    """Return possible extension keys, preferring longest compound ext first (e.g., .tar.gz)."""
    name = os.path.basename(filename).lower()
    parts = name.split('.')
    if len(parts) <= 1:
        return []
    cands = []
    # try .part.part ... down to single extension
    for i in range(1, len(parts)):
        ext = '.' + '.'.join(parts[i:])
        cands.append(ext)
    # ensure single ext is last if not already
    single = os.path.splitext(name)[1]
    if single and single not in cands:
        cands.append(single)
    # dedupe while preserving order
    seen, ordered = set(), []
    for e in cands:
        if e not in seen:
            ordered.append(e)
            seen.add(e)
    return ordered

def _safe_join(root: str, *paths: str) -> str:
    """Join and assert result is within root."""
    target = os.path.abspath(os.path.join(root, *paths))
    if not _is_subpath(target, root):
        raise ValueError(f"Refusing to write outside root: {target}")
    return target

def _collect_files(
    base_folder: str,
    include_subfolders: bool,
    *,
    skip_hidden: bool,
    exclude_dirs: Optional[List[str]],
    exclude_files: Optional[List[str]],
    max_depth: Optional[int],
) -> List[Tuple[str, str]]:
    """Return (dirpath, filename) tuples under base_folder."""
    files: List[Tuple[str, str]] = []
    base_folder = os.path.abspath(base_folder)

    def prune_dirnames(dirnames: List[str], cur_depth: int) -> List[str]:
        pruned: List[str] = []
        for d in dirnames:
            if max_depth is not None and cur_depth + 1 > max_depth:
                continue
            if skip_hidden and d.startswith('.'):
                continue
            if exclude_dirs and any(fnmatch.fnmatch(d, pat) for pat in exclude_dirs):
                continue
            pruned.append(d)
        return pruned

    if include_subfolders:
        for dirpath, dirnames, filenames in os.walk(base_folder, topdown=True):
            rel = os.path.relpath(dirpath, base_folder)
            depth = 0 if rel == '.' else rel.count(os.sep) + 1  # number of components below base
            dirnames[:] = prune_dirnames(dirnames, depth)
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                if skip_hidden and _is_hidden(fn, full):
                    continue
                if exclude_files and any(fnmatch.fnmatch(fn, pat) for pat in exclude_files):
                    continue
                if os.path.isfile(full):
                    files.append((dirpath, fn))
    else:
        try:
            entries = os.listdir(base_folder)
        except Exception:
            raise
        for fn in entries:
            full = os.path.join(base_folder, fn)
            if skip_hidden and _is_hidden(fn, full):
                continue
            if exclude_files and any(fnmatch.fnmatch(fn, pat) for pat in exclude_files):
                continue
            if os.path.isfile(full):
                files.append((base_folder, fn))
    return files

# ---- Advanced Rule System ----

class AdvancedRule:
    """Base class for advanced file organization rules."""
    
    def __init__(self, rule_data: Dict[str, Any]):
        self.type = rule_data.get('type', '')
        self.destination = rule_data.get('destination', '')
        
    def matches(self, file_path: str, file_stats: os.stat_result) -> bool:
        """Check if this rule matches the given file."""
        raise NotImplementedError
        
    def get_destination(self, file_path: str, file_stats: os.stat_result) -> str:
        """Get the destination folder for this file, with template substitution."""
        dest = self.destination
        
        # Template substitution for date-based destinations
        if '{{' in dest:
            mtime = datetime.fromtimestamp(file_stats.st_mtime)
            dest = dest.replace('{{year}}', str(mtime.year))
            dest = dest.replace('{{month}}', mtime.strftime('%B'))
            dest = dest.replace('{{month_num}}', f'{mtime.month:02d}')
            dest = dest.replace('{{day}}', f'{mtime.day:02d}')
            
        return dest

class FilenamePatternRule(AdvancedRule):
    """Rule that matches files based on filename patterns (wildcards or regex)."""
    
    def __init__(self, rule_data: Dict[str, Any]):
        super().__init__(rule_data)
        self.pattern = rule_data.get('pattern', '')
        self.use_regex = rule_data.get('use_regex', False)
        
    def matches(self, file_path: str, file_stats: os.stat_result) -> bool:
        filename = os.path.basename(file_path)
        
        if self.use_regex:
            try:
                return bool(re.match(self.pattern, filename, re.IGNORECASE))
            except re.error:
                return False
        else:
            return fnmatch.fnmatch(filename.lower(), self.pattern.lower())

class DateRule(AdvancedRule):
    """Rule that matches files based on modification/creation date."""
    
    def __init__(self, rule_data: Dict[str, Any]):
        super().__init__(rule_data)
        self.condition = rule_data.get('condition', 'older_than_days')
        self.value = rule_data.get('value', 0)
        
    def matches(self, file_path: str, file_stats: os.stat_result) -> bool:
        current_time = time.time()
        # For date rules, use modification time (st_mtime) as it's more reliable for user-set dates
        file_time = file_stats.st_mtime
        age_days = (current_time - file_time) / 86400.0
        
        if self.condition == 'older_than_days':
            return age_days > self.value
        elif self.condition == 'newer_than_days':
            return age_days < self.value
        elif self.condition == 'between_days':
            min_days, max_days = self.value if isinstance(self.value, list) else [0, self.value]
            return min_days <= age_days <= max_days
            
        return False

class SizeRule(AdvancedRule):
    """Rule that matches files based on file size."""
    
    def __init__(self, rule_data: Dict[str, Any]):
        super().__init__(rule_data)
        self.condition = rule_data.get('condition', 'larger_than_mb')
        self.value = rule_data.get('value', 0)
        
    def matches(self, file_path: str, file_stats: os.stat_result) -> bool:
        size_bytes = file_stats.st_size
        
        if self.condition == 'larger_than_mb':
            return size_bytes > (self.value * 1024 * 1024)
        elif self.condition == 'smaller_than_mb':
            return size_bytes < (self.value * 1024 * 1024)
        elif self.condition == 'larger_than_kb':
            return size_bytes > (self.value * 1024)
        elif self.condition == 'smaller_than_kb':
            return size_bytes < (self.value * 1024)
        elif self.condition == 'between_mb':
            min_mb, max_mb = self.value if isinstance(self.value, list) else [0, self.value]
            min_bytes = min_mb * 1024 * 1024
            max_bytes = max_mb * 1024 * 1024
            return min_bytes <= size_bytes <= max_bytes
            
        return False

def _load_advanced_rules(config: Dict[str, Any]) -> List[AdvancedRule]:
    """Load advanced rules from config."""
    rules = []
    advanced_rules_data = config.get('advanced_rules', [])
    
    for rule_data in advanced_rules_data:
        rule_type = rule_data.get('type', '')
        
        if rule_type == 'filename_pattern':
            rules.append(FilenamePatternRule(rule_data))
        elif rule_type == 'date':
            rules.append(DateRule(rule_data))
        elif rule_type == 'size':
            rules.append(SizeRule(rule_data))
            
    return rules

def _match_advanced_rules(file_path: str, advanced_rules: List[AdvancedRule]) -> Optional[str]:
    """Check if file matches any advanced rule and return destination."""
    try:
        file_stats = os.stat(file_path)
        
        for rule in advanced_rules:
            if rule.matches(file_path, file_stats):
                return rule.get_destination(file_path, file_stats)
                
    except (OSError, IOError):
        # If we can't get file stats, skip advanced rules
        pass
        
    return None

# ---- Undo System ----

def _get_undo_log_path() -> str:
    """Get path to the undo log file."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, 'undo_log.json')

def _log_operation(operation_type: str, source_path: str, dest_path: str, timestamp: float = None) -> None:
    """Log a file operation for potential undo."""
    if timestamp is None:
        timestamp = time.time()
        
    log_entry = {
        'operation': operation_type,  # 'move' or 'copy'
        'source': source_path,
        'destination': dest_path,
        'timestamp': timestamp,
        'datetime': datetime.fromtimestamp(timestamp).isoformat()
    }
    
    log_path = _get_undo_log_path()
    
    # Load existing log or create new
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        log_data = {'operations': []}
    
    # Add new operation
    log_data['operations'].append(log_entry)
    
    # Keep only last 1000 operations to prevent log from growing too large
    if len(log_data['operations']) > 1000:
        log_data['operations'] = log_data['operations'][-1000:]
    
    # Save updated log
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2)
    except Exception:
        # If we can't log, continue silently (don't break the main operation)
        pass

def undo_last_operation() -> Dict[str, List[str]]:
    """
    Undo the last organization operation.
    Returns a dictionary with 'reverted', 'errors', and 'info' lists.
    """
    log_path = _get_undo_log_path()
    
    if not os.path.exists(log_path):
        return {'reverted': [], 'errors': [], 'info': ['No operations to undo']}
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return {'reverted': [], 'errors': [f'Cannot read undo log: {e}'], 'info': []}
    
    operations = log_data.get('operations', [])
    if not operations:
        return {'reverted': [], 'errors': [], 'info': ['No operations to undo']}
    
    # Find the most recent batch of operations (same timestamp within 1 second)
    last_op = operations[-1]
    last_timestamp = last_op['timestamp']
    
    # Get all operations from the same batch
    batch_ops = []
    for op in reversed(operations):
        if abs(op['timestamp'] - last_timestamp) <= 1.0:  # Within 1 second
            batch_ops.append(op)
        else:
            break
    
    results = {'reverted': [], 'errors': [], 'info': []}
    reverted_count = 0
    
    # Undo operations in reverse order
    for op in batch_ops:
        source = op['source']
        dest = op['destination'] 
        op_type = op['operation']
        
        try:
            if op_type == 'move' and os.path.exists(dest):
                # For moves, move the file back to original location
                if os.path.exists(source):
                    # If source location is occupied, find a new name
                    source = _next_free_path(source)
                    
                # Ensure source directory exists
                source_dir = os.path.dirname(source)
                if source_dir:
                    os.makedirs(source_dir, exist_ok=True)
                    
                shutil.move(dest, source)
                results['reverted'].append(f"Moved {os.path.basename(dest)} back to {source}")
                reverted_count += 1
                
            elif op_type == 'copy' and os.path.exists(dest):
                # For copies, just delete the copy (original is still in place)
                os.remove(dest)
                results['reverted'].append(f"Removed copy {dest}")
                reverted_count += 1
                
            else:
                results['info'].append(f"Skipped {dest} (file not found)")
                
        except Exception as e:
            results['errors'].append(f"Failed to undo {dest}: {e}")
    
    # Remove the undone operations from the log
    if reverted_count > 0:
        log_data['operations'] = operations[:-len(batch_ops)]
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2)
        except Exception as e:
            results['errors'].append(f"Failed to update undo log: {e}")
    
    if reverted_count > 0:
        results['info'].append(f"Successfully undid {reverted_count} operations")
    
    return results

# ---- Profile/Preset System ----

def get_available_profiles() -> List[str]:
    """Get list of available profile names."""
    config_path = _get_config_path()
    if not os.path.exists(config_path):
        return ["default"]
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        
        if "profiles" in cfg:
            return list(cfg["profiles"].keys())
        else:
            return ["default"]  # Legacy config
    except (json.JSONDecodeError, IOError):
        return ["default"]

def get_active_profile_name() -> str:
    """Get the name of the currently active profile."""
    config_path = _get_config_path()
    if not os.path.exists(config_path):
        return "default"
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        return cfg.get("active_profile", "default")
    except (json.JSONDecodeError, IOError):
        return "default"

def get_profile_data(profile_name: str = None) -> Dict[str, Any]:
    """Get profile data. If profile_name is None, gets active profile."""
    config_path = _get_config_path()
    if not os.path.exists(config_path):
        return {"rules": {}, "advanced_rules": []}
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            
        if profile_name is None:
            profile_name = cfg.get("active_profile", "default")
            
        # Handle legacy config format
        if "profiles" not in cfg:
            if profile_name == "default":
                return {
                    "rules": cfg.get("rules", {}),
                    "advanced_rules": cfg.get("advanced_rules", [])
                }
            else:
                return {"rules": {}, "advanced_rules": []}
        
        profiles = cfg.get("profiles", {})
        return profiles.get(profile_name, {"rules": {}, "advanced_rules": []})
        
    except (json.JSONDecodeError, IOError):
        return {"rules": {}, "advanced_rules": []}

def save_profile(profile_name: str, profile_data: Dict[str, Any]) -> bool:
    """Save a profile. Returns True on success."""
    config_path = _get_config_path()
    
    try:
        # Load existing config or create new
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        else:
            cfg = {}
            
        # Convert legacy format to new format if needed
        if "profiles" not in cfg:
            # Convert current config to default profile
            default_profile = {
                "rules": cfg.get("rules", {}),
                "advanced_rules": cfg.get("advanced_rules", [])
            }
            cfg = {
                "active_profile": cfg.get("active_profile", "default"),
                "profiles": {
                    "default": default_profile
                }
            }
            
        # Save the profile
        cfg["profiles"][profile_name] = profile_data
        
        # Write updated config
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
            
        return True
    except Exception:
        return False

def delete_profile(profile_name: str) -> bool:
    """Delete a profile. Cannot delete 'default' or currently active profile."""
    if profile_name == "default":
        return False  # Cannot delete default
        
    config_path = _get_config_path()
    if not os.path.exists(config_path):
        return False
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            
        if "profiles" not in cfg:
            return False  # Legacy format
            
        active_profile = cfg.get("active_profile", "default")
        if profile_name == active_profile:
            return False  # Cannot delete active profile
            
        if profile_name not in cfg["profiles"]:
            return False  # Profile doesn't exist
            
        del cfg["profiles"][profile_name]
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
            
        return True
    except Exception:
        return False

def set_active_profile(profile_name: str) -> bool:
    """Set the active profile. Returns True on success."""
    config_path = _get_config_path()
    
    try:
        # Load existing config
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        else:
            cfg = {"rules": {}, "advanced_rules": []}
            
        # Convert legacy format if needed
        if "profiles" not in cfg:
            default_profile = {
                "rules": cfg.get("rules", {}),
                "advanced_rules": cfg.get("advanced_rules", [])
            }
            cfg = {
                "active_profile": "default",
                "profiles": {
                    "default": default_profile
                }
            }
            
        # Check if profile exists
        if profile_name not in cfg["profiles"]:
            return False
            
        cfg["active_profile"] = profile_name
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
            
        return True
    except Exception:
        return False

# ---- Duplicate File Detection System ----

def _calculate_file_hash(file_path: str, hash_algorithm: str = 'md5') -> str:
    """Calculate hash of a file. Returns empty string on error."""
    try:
        if hash_algorithm.lower() == 'md5':
            hasher = hashlib.md5()
        elif hash_algorithm.lower() == 'sha256':
            hasher = hashlib.sha256()
        else:
            hasher = hashlib.md5()  # Default fallback
            
        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    except (IOError, OSError):
        return ""

def find_duplicate_files(
    folder_path: str,
    include_subfolders: bool = True,
    skip_hidden: bool = True,
    exclude_dirs: Optional[List[str]] = None,
    exclude_files: Optional[List[str]] = None,
    min_file_size: int = 0,
    hash_algorithm: str = 'md5',
    on_progress: Optional[Callable[[str, int, int], None]] = None
) -> Dict[str, List[Tuple[str, str]]]:
    """
    Find duplicate files in a folder.
    
    Returns a dictionary where keys are file hashes and values are lists of 
    (file_path, relative_path) tuples that have the same content.
    
    Args:
        folder_path: Root folder to scan
        include_subfolders: Whether to scan subdirectories
        skip_hidden: Whether to skip hidden files
        exclude_dirs: Directory names to exclude
        exclude_files: File patterns to exclude
        min_file_size: Minimum file size in bytes to consider
        hash_algorithm: 'md5' or 'sha256'
        on_progress: Callback for progress updates (current_file, processed, total)
    """
    folder_path = os.path.abspath(folder_path)
    
    # Collect all files first
    file_list = _collect_files(
        folder_path,
        include_subfolders,
        skip_hidden=skip_hidden,
        exclude_dirs=exclude_dirs,
        exclude_files=exclude_files,
        max_depth=None
    )
    
    # Group files by size first (optimization - files of different sizes can't be duplicates)
    size_groups: Dict[int, List[Tuple[str, str]]] = defaultdict(list)
    
    total_files = len(file_list)
    processed = 0
    
    for dirpath, filename in file_list:
        full_path = os.path.join(dirpath, filename)
        
        try:
            file_size = os.path.getsize(full_path)
            
            # Skip files smaller than minimum size
            if file_size < min_file_size:
                processed += 1
                continue
                
            relative_path = os.path.relpath(full_path, folder_path)
            size_groups[file_size].append((full_path, relative_path))
            
        except (OSError, IOError):
            pass  # Skip files we can't read
            
        processed += 1
        if on_progress:
            on_progress(filename, processed, total_files)
    
    # Now check for duplicates within each size group
    duplicates: Dict[str, List[Tuple[str, str]]] = {}
    
    for file_size, files_with_size in size_groups.items():
        if len(files_with_size) < 2:
            continue  # No duplicates possible with only one file
            
        # Calculate hashes for files with the same size
        hash_groups: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        
        for full_path, relative_path in files_with_size:
            file_hash = _calculate_file_hash(full_path, hash_algorithm)
            if file_hash:  # Only consider files we could hash
                hash_groups[file_hash].append((full_path, relative_path))
                
        # Add groups with multiple files as duplicates
        for file_hash, files_with_hash in hash_groups.items():
            if len(files_with_hash) > 1:
                duplicates[file_hash] = files_with_hash
                
    return duplicates

def handle_duplicates(
    duplicates: Dict[str, List[Tuple[str, str]]],
    action: str = 'move_to_folder',
    duplicate_folder: str = 'Duplicates',
    keep_criteria: str = 'first',  # 'first', 'largest_path', 'shortest_path'
    dry_run: bool = True,
    on_file_processed: Optional[Callable[[str, Optional[str], str, Optional[str]], None]] = None
) -> Dict[str, List[Tuple[str, Optional[str]]]]:
    """
    Handle detected duplicates according to specified action.
    
    Args:
        duplicates: Dictionary from find_duplicate_files
        action: 'move_to_folder', 'delete', 'skip'
        duplicate_folder: Folder name for moved duplicates
        keep_criteria: Which file to keep when handling duplicates
        dry_run: Whether to simulate the operation
        on_file_processed: Callback for progress
        
    Returns:
        Results dictionary similar to organize_folder
    """
    results: Dict[str, List[Tuple[str, Optional[str]]]] = {
        'moved': [],
        'copied': [],
        'deleted': [],
        'skipped': [],
        'errors': [],
    }
    
    if dry_run:
        results.update({
            'would-moved': [],
            'would-deleted': [],
            'would-skipped': []
        })
    
    for file_hash, duplicate_files in duplicates.items():
        if len(duplicate_files) < 2:
            continue
            
        # Determine which file to keep
        if keep_criteria == 'first':
            keep_file = duplicate_files[0]
            process_files = duplicate_files[1:]
        elif keep_criteria == 'shortest_path':
            keep_file = min(duplicate_files, key=lambda x: len(x[1]))
            process_files = [f for f in duplicate_files if f != keep_file]
        elif keep_criteria == 'largest_path':
            keep_file = max(duplicate_files, key=lambda x: len(x[1]))
            process_files = [f for f in duplicate_files if f != keep_file]
        else:
            keep_file = duplicate_files[0]
            process_files = duplicate_files[1:]
            
        for full_path, relative_path in process_files:
            filename = os.path.basename(full_path)
            
            try:
                if action == 'skip':
                    if dry_run:
                        results['would-skipped'].append((filename, None))
                        if on_file_processed:
                            on_file_processed(filename, None, 'would-skip', 'duplicate')
                    else:
                        results['skipped'].append((filename, None))
                        if on_file_processed:
                            on_file_processed(filename, None, 'skipped', 'duplicate')
                            
                elif action == 'delete':
                    if dry_run:
                        results['would-deleted'].append((filename, None))
                        if on_file_processed:
                            on_file_processed(filename, None, 'would-delete', 'duplicate')
                    else:
                        os.remove(full_path)
                        results['deleted'].append((filename, None))
                        if on_file_processed:
                            on_file_processed(filename, None, 'deleted', 'duplicate')
                            
                elif action == 'move_to_folder':
                    # Create duplicate folder structure
                    source_dir = os.path.dirname(full_path)
                    dest_dir = os.path.join(source_dir, duplicate_folder)
                    
                    if dry_run:
                        results['would-moved'].append((filename, duplicate_folder))
                        if on_file_processed:
                            on_file_processed(filename, duplicate_folder, 'would-move', 'duplicate')
                    else:
                        os.makedirs(dest_dir, exist_ok=True)
                        dest_path = _next_free_path(os.path.join(dest_dir, filename))
                        shutil.move(full_path, dest_path)
                        results['moved'].append((filename, duplicate_folder))
                        if on_file_processed:
                            on_file_processed(filename, duplicate_folder, 'moved', 'duplicate')
                            
            except Exception as e:
                results['errors'].append((filename, None))
                if on_file_processed:
                    on_file_processed(filename, None, 'error', f'duplicate handling: {e}')
                    
    return results

def _next_free_path(path: str) -> str:
    """Find next available filename if path exists."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while True:
        candidate = f"{base} ({i}){ext}"
        if not os.path.exists(candidate):
            return candidate
        i += 1

def organize_folder(
    folder_path: str,
    on_file_processed: Optional[Callable[[str, Optional[str], str, Optional[str]], None]] = None,
    *,
    include_subfolders: bool = False,
    mode: str = 'move',  # 'move' | 'copy'
    dry_run: bool = False,
    unknown_destination: Optional[str] = None,
    allow_dangerous: bool = False,
    preserve_tree: bool = False,
    min_age_days: Optional[int] = None,
    skip_hidden: bool = True,
    exclude_dirs: Optional[List[str]] = None,
    exclude_files: Optional[List[str]] = None,
    max_depth: Optional[int] = None,
    allow_symlinks: bool = False,
    delete_junk: bool = False,
    junk_patterns: Optional[List[str]] = None,
    junk_min_age_days: Optional[float] = None,
) -> Dict[str, List[Tuple[str, Optional[str]]]]:
    """
    Organize files in 'folder_path' based on rules in config.json.
    - Respects compound extensions (.tar.gz) and case.
    - Prevents path traversal/absolute destinations.
    - Skips app-like subdirectories, hidden files, symlinks (by default), and protected extensions.
    - Collision-safe writes with 'file (1).ext' style.
    - Optional: preserve source subfolder tree under each destination, minimum file age, and directory/filename excludes.
    """
    if mode not in ('move', 'copy'):
        raise ValueError(f"Invalid mode: {mode}")
    if not os.path.isdir(folder_path):
        raise FileNotFoundError(f"Folder does not exist: {folder_path}")

    folder_path = os.path.abspath(folder_path)

    # Safety guardrail
    if not allow_dangerous and _is_dangerous_folder(folder_path):
        msg = f"Refusing to organize dangerous folder: {folder_path}"
        if on_file_processed:
            on_file_processed(folder_path, None, 'error', msg)
        raise ValueError(msg)

    # Load active profile data
    try:
        profile_data = get_profile_data()  # Gets active profile
        raw_rules: Dict[str, str] = profile_data.get('rules', {})
        rules = _normalize_rules(raw_rules)
        
        # Load advanced rules
        advanced_rules = _load_advanced_rules(profile_data)
    except Exception as e:
        msg = f"Failed to load profile configuration: {e}"
        if on_file_processed:
            on_file_processed('config.json', None, 'error', msg)
        raise ValueError(msg)

    # Unknown destination sanity
    if unknown_destination:
        unknown_destination = unknown_destination.strip()
        # reuse normalizer checks by simulating a single rule
        _ = _normalize_rules({'.__unknown__': unknown_destination})
        # keep as provided

    # Effective excludes
    eff_exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    if exclude_dirs:
        eff_exclude_dirs.update(exclude_dirs)

    # Build list of files
    try:
        file_list = _collect_files(
            folder_path,
            include_subfolders,
            skip_hidden=skip_hidden,
            exclude_dirs=list(eff_exclude_dirs) if include_subfolders else None,
            exclude_files=exclude_files,
            max_depth=max_depth,
        )
    except Exception as e:
        msg = f"Cannot list folder '{folder_path}': {e}"
        if on_file_processed:
            on_file_processed(folder_path, None, 'error', msg)
        raise

    results: Dict[str, List[Tuple[str, Optional[str]]]] = {
        'moved': [],
        'copied': [],
        'skipped': [],
        'errors': [],
        'deleted': [],
        # dry-run buckets created lazily: 'would-moved', 'would-copied', 'would-deleted'
    }

    # Cache for app-like directory checks
    appdir_cache: Dict[str, bool] = {}

    def _next_free_path(path: str) -> str:
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        i = 1
        while True:
            candidate = f"{base} ({i}){ext}"
            if not os.path.exists(candidate):
                return candidate
            i += 1

    def _file_age_days(fullpath: str) -> float:
        st = os.stat(fullpath)
        # use current time relative calculation for clarity
        import time
        return (time.time() - max(st.st_mtime, st.st_ctime)) / 86400.0

    def _is_junk(basename: str, patterns: List[str]) -> bool:
        name = basename.lower()
        for pat in patterns:
            if fnmatch.fnmatch(name, pat):
                return True
        return False

    for dirpath, file in file_list:
        source_path = os.path.join(dirpath, file)

        # Skip symlinks unless explicitly allowed
        if not allow_symlinks and os.path.islink(source_path):
            results['skipped'].append((file, None))
            if on_file_processed:
                on_file_processed(file, None, 'skipped', 'symlink')
            continue

        # Skip files inside app-like subdirectories when traversing subfolders
        if include_subfolders and dirpath != folder_path:
            is_app = appdir_cache.get(dirpath)
            if is_app is None:
                is_app = _looks_like_app_dir(dirpath)
                appdir_cache[dirpath] = is_app
            if is_app:
                results['skipped'].append((file, None))
                if on_file_processed:
                    on_file_processed(os.path.join(dirpath, file), None, 'skipped', 'app-like folder')
                continue

        # Junk deletion (applies before protected-extension skip; gated by age)
        ext_lower = os.path.splitext(file)[1].lower()
        if delete_junk:
            patterns = [p.lower() for p in (junk_patterns or DEFAULT_JUNK_PATTERNS)]
            try:
                age_days = _file_age_days(source_path)
            except Exception:
                age_days = 0.0
            # Use stricter of provided junk_min_age_days and global min_age_days (default 14 days)
            min_for_delete = 14.0
            if min_age_days is not None:
                try:
                    min_for_delete = max(min_for_delete, float(min_age_days))
                except Exception:
                    pass
            if junk_min_age_days is not None:
                try:
                    min_for_delete = max(min_for_delete, float(junk_min_age_days))
                except Exception:
                    pass
            if _is_junk(file, patterns) and age_days >= min_for_delete:
                try:
                    if dry_run:
                        results.setdefault('would-deleted', []).append((file, None))
                        if on_file_processed:
                            on_file_processed(file, None, 'would-delete', f'junk ≥{int(min_for_delete)}d')
                    else:
                        os.remove(source_path)
                        results['deleted'].append((file, None))
                        if on_file_processed:
                            on_file_processed(file, None, 'deleted', 'junk')
                    continue  # handled
                except Exception as e:
                    results['errors'].append((file, None))
                    if on_file_processed:
                        on_file_processed(file, None, 'error', f'junk delete: {e}')
                    continue

        # Skip protected extensions entirely for move/copy
        if ext_lower in PROTECTED_EXTS:
            results['skipped'].append((file, None))
            if on_file_processed:
                on_file_processed(file, None, 'skipped', 'protected extension')
            continue

        # Minimum age filter (days)
        if min_age_days is not None:
            try:
                # Compute age in days relative to "now"
                # (Avoid calling time.time() per file; relative comparison
                # is equivalent by comparing mtimes directly.)
                import time
                age_days = (time.time() - max(os.path.getmtime(source_path), os.path.getctime(source_path))) / 86400.0
                if age_days < float(min_age_days):
                    results['skipped'].append((file, None))
                    if on_file_processed:
                        on_file_processed(file, None, 'skipped', f'younger than {min_age_days}d')
                    continue
            except Exception:
                # If we can’t read timestamps, treat as eligible
                pass

        # Determine destination based on rules
        # Check advanced rules first (they are more specific)
        destination: Optional[str] = _match_advanced_rules(source_path, advanced_rules)
        
        # If no advanced rule matched, try traditional extension-based rules
        if destination is None:
            for ek in _ext_candidates(file):
                if ek in rules:
                    destination = rules[ek]
                    break
            
        # Fall back to unknown destination if nothing matched
        if destination is None and unknown_destination:
            destination = unknown_destination

        if destination:
            # Build destination folder (optionally mirror source subpath)
            rel_sub = os.path.relpath(dirpath, folder_path) if preserve_tree else ''
            destination_folder_rel = os.path.join(destination, rel_sub) if rel_sub != '.' else destination
            # Safe-join under the organizing root
            destination_folder_abs = _safe_join(folder_path, destination_folder_rel)
            try:
                os.makedirs(destination_folder_abs, exist_ok=True)
                dest_path = _next_free_path(_safe_join(destination_folder_abs, file))

                if dry_run:
                    status = 'would-move' if mode == 'move' else 'would-copy'
                    key = 'would-moved' if mode == 'move' else 'would-copied'
                    results.setdefault(key, []).append((file, destination_folder_rel))
                    if on_file_processed:
                        on_file_processed(file, destination_folder_rel, status, None)
                else:
                    # Record timestamp for this batch of operations
                    import time as time_module
                    operation_timestamp = time_module.time()
                    
                    if mode == 'move':
                        shutil.move(source_path, dest_path)
                        _log_operation('move', source_path, dest_path, operation_timestamp)
                        results['moved'].append((file, destination_folder_rel))
                        if on_file_processed:
                            on_file_processed(file, destination_folder_rel, 'moved', None)
                    else:
                        shutil.copy2(source_path, dest_path)
                        _log_operation('copy', source_path, dest_path, operation_timestamp)
                        results['copied'].append((file, destination_folder_rel))
                        if on_file_processed:
                            on_file_processed(file, destination_folder_rel, 'copied', None)
            except Exception as e:
                results['errors'].append((file, destination))
                if on_file_processed:
                    on_file_processed(file, destination, 'error', str(e))
        else:
            results['skipped'].append((file, None))
            if on_file_processed:
                on_file_processed(file, None, 'skipped', 'no matching rule')

    return results
