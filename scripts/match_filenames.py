#!/usr/bin/env python3

import csv
import os

# Root of your website
BASE_DIR = "/nfs/hatops/ar0/hatpi-website"

# Directories to search (relative to BASE_DIR)
SEARCH_DIRS = ["RED", "SUB"]

# If you only want to search IHU01 to IHU05
IHU_LIST = [f"ihu0{i}" for i in range(1,6)]
# i.e. ["ihu01","ihu02","ihu03","ihu04","ihu05"]

# If you only want to search *recent* date folders (e.g. starting from 1-20250310),
# set a cutoff. If None, it will scan all date folders that start with "1-".
MIN_DATEFOLDER = "1-20250310"  # or None to search all

# INPUT: CSV of filenames
INPUT_CSV = "/nfs/hatops/ar0/hatpi-website/tagged_files.csv"

# OUTPUT: CSV that will be created (or overwritten)
OUTPUT_CSV = "tagged_with_paths.csv"

# If True, once the script has found all filenames, it will stop scanning further directories.
SHORT_CIRCUIT_WHEN_ALL_FOUND = True

def is_valid_date_folder(folder):
    """
    Checks if the folder name matches '1-YYYYMMDD' format
    and optionally is >= MIN_DATEFOLDER if that's set.
    """
    if not folder.startswith("1-"):
        return False
    if len(folder) != 10:  # e.g. "1-20250314" => 10 chars
        return False
    # e.g. "1-20250314" < "1-20250310"? Then skip.
    if MIN_DATEFOLDER is not None and folder < MIN_DATEFOLDER:
        return False
    return True

def main():
    # 1) Read all filenames from the input CSV into a list.
    #    We assume one filename per line, no header.
    with open(INPUT_CSV, "r", newline='', encoding="utf-8") as f:
        reader = csv.reader(f)
        filenames = [row[0].strip() for row in reader if row]

    # We'll store the best guess path for each filename in a dict
    results = {}
    for fn in filenames:
        results[fn] = "NOT_FOUND"  # default

    # Count how many remain unfound:
    unfound_count = len(filenames)

    print(f"Loaded {len(filenames)} filenames from {INPUT_CSV}.")
    print("Starting directory scan...")

    # 2) Loop over SEARCH_DIRS, e.g. "RED" and "SUB"
    for subdir in SEARCH_DIRS:
        subdir_path = os.path.join(BASE_DIR, subdir)
        if not os.path.isdir(subdir_path):
            print(f"Warning: {subdir_path} is not a directory. Skipping.")
            continue

        # 3) Inside each "RED" or "SUB", loop over date folders
        for date_folder in sorted(os.listdir(subdir_path)):
            date_folder_path = os.path.join(subdir_path, date_folder)
            if not os.path.isdir(date_folder_path):
                continue
            if not is_valid_date_folder(date_folder):
                continue

            # 4) Inside each date folder, loop over IHU01..IHU05
            for ihu_folder in IHU_LIST:
                ihu_path = os.path.join(date_folder_path, ihu_folder)
                if not os.path.isdir(ihu_path):
                    # skip if this IHU folder doesn't exist
                    continue

                # 5) Now list the files in that IHU folder
                try:
                    files_in_ihu = os.listdir(ihu_path)
                except Exception as e:
                    print(f"Error reading {ihu_path}: {e}")
                    continue

                for file_on_disk in files_in_ihu:
                    # If it’s one of the filenames we're looking for, and not found yet, record it
                    if file_on_disk in results and results[file_on_disk] == "NOT_FOUND":
                        # Build a site-relative path
                        full_rel_path = f"/{subdir}/{date_folder}/{ihu_folder}/{file_on_disk}"
                        results[file_on_disk] = full_rel_path
                        unfound_count -= 1

                        print(f"Found match: '{file_on_disk}' => {full_rel_path}")
                        if SHORT_CIRCUIT_WHEN_ALL_FOUND and unfound_count == 0:
                            print("All filenames have been located. Stopping early.")
                            break

                # If we’re short-circuiting and everything was found, break out:
                if SHORT_CIRCUIT_WHEN_ALL_FOUND and unfound_count == 0:
                    break

            # If we’re short-circuiting and everything was found, break out:
            if SHORT_CIRCUIT_WHEN_ALL_FOUND and unfound_count == 0:
                break

        # If we’re short-circuiting and everything was found, break out:
        if SHORT_CIRCUIT_WHEN_ALL_FOUND and unfound_count == 0:
            break

    # 6) Write out results to OUTPUT_CSV
    with open(OUTPUT_CSV, "w", newline='', encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(["filename", "full_path"])
        for fn in filenames:
            writer.writerow([fn, results[fn]])

    print(f"\nDone. Wrote {OUTPUT_CSV}.")
    print(f"Found matches for {len(filenames) - unfound_count}/{len(filenames)} filenames.")
    if unfound_count > 0:
        print("Some files were not found. They will appear as 'NOT_FOUND' in the CSV.")


if __name__ == "__main__":
    main()
