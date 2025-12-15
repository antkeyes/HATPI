#!/usr/bin/env python3
import os
import json
import sys

# --- CONFIGURATION ---
# Path to your keyboard_flags.json file (adjust if necessary)
INPUT_JSON_PATH = 'flags_backup.json'
# Path to write the updated JSON
OUTPUT_JSON_PATH = 'keyboard_flags_updated_paths.json'
# Base directory where your RED and SUB folders are located.
# For example, if your file structure is like "/path/to/hatpi/RED/...", then:
BASE_DIR = '/nfs/hatops/ar0/hatpi-website'  # CHANGE THIS to your actual base directory

# --- HELPER FUNCTIONS ---

def get_prefix(filename):
    """
    Given a filename like '1-505931_03-red-bin4.jpg' or '1-505931_03-sub-bin4.jpg',
    return the prefix up through the type indicator.
    For example, for '-red-' it returns '1-505931_03-red-'
    """
    for marker in ['-red-', '-sub-']:
        pos = filename.lower().find(marker)
        if pos != -1:
            # Include the marker in the prefix
            return filename[:pos + len(marker)]
    return None

def update_path(old_path):
    """
    Given an old file path (e.g. "/RED/1-20250314/ihu03/1-505931_03-red-bin4.jpg"),
    check the corresponding directory (under BASE_DIR) for a file that starts with the prefix.
    If found, return the new path (starting with '/') using the new filename.
    Otherwise, return the original old_path.
    """
    # Remove any trailing slash (if any)
    old_path = old_path.rstrip('/')
    directory = os.path.dirname(old_path)  # e.g. "/RED/1-20250314/ihu03"
    base_filename = os.path.basename(old_path)
    prefix = get_prefix(base_filename)
    if not prefix:
        # No marker found; return the original path.
        return old_path

    # Build the full directory path on disk
    full_dir = os.path.join(BASE_DIR, directory.lstrip('/'))
    if not os.path.isdir(full_dir):
        print(f"Warning: Directory '{full_dir}' does not exist.", file=sys.stderr)
        return old_path

    try:
        candidates = os.listdir(full_dir)
    except Exception as e:
        print(f"Error listing directory '{full_dir}': {e}", file=sys.stderr)
        return old_path

    # Look for a candidate that starts with the prefix and is not exactly the same as the old base filename.
    for candidate in candidates:
        if candidate.startswith(prefix) and candidate != base_filename:
            # Return the new file path, preserving the leading "/"
            new_path = os.path.join(directory, candidate)
            # Normalize to use forward slashes:
            return new_path.replace(os.path.sep, '/')
    # If no candidate was found, return the original
    return old_path

# --- MAIN SCRIPT ---

def migrate_keyboard_flags():
    # Read the original JSON file
    try:
        with open(INPUT_JSON_PATH, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {INPUT_JSON_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

    updated_data = {}

    # Iterate over each key (file path)
    for old_path, details in data.items():
        # Update the path if possible.
        new_path = update_path(old_path)
        if new_path != old_path:
            print(f"Updating:\n  Old: {old_path}\n  New: {new_path}")
        updated_data[new_path] = details

    # Write the updated JSON to a new file
    try:
        with open(OUTPUT_JSON_PATH, 'w') as f:
            json.dump(updated_data, f, indent=4)
        print(f"Updated JSON written to {OUTPUT_JSON_PATH}")
    except Exception as e:
        print(f"Error writing to {OUTPUT_JSON_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    migrate_keyboard_flags()
