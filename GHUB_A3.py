#!/usr/bin/env python3
# -------------------------------------------------------------
# Logitech G-Hub Profile Editor (settings.db) w/ Icon Conversion
# -------------------------------------------------------------
# 1) Reads "settings.db" from "C:\\Users\\Bill\\AppData\\Local\\LGHUB"
# 2) Connects to table "DATA" and column "FILE" (BLOB) containing JSON
# 3) Decodes BLOB -> JSON, finds "applications" -> "applications" array
# 4) Lists all profiles in a Tkinter GUI, lets you rename them, change
#    application path, and set icon posterPath
# 5) On Browse: we convert chosen file (PNG/JPG/ICO) to BMP and store/overwrite
#    in "C:\\Users\\Bill\\AppData\\Local\\LGHUB\\icon_cache\\<something>.bmp"
# 6) We then update 'posterPath' in the JSON and display a preview
# 7) On Save, we write the updated JSON (BLOB) to DB
# Logging ~7/10 for debugging

import sqlite3
import json
import os
import re
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

# -------------------------------------------------------------
# Logging Configuration
# -------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(asctime)s - %(message)s'
)

# -------------------------------------------------------------
# DB Configuration
# -------------------------------------------------------------
DB_PATH = r"C:\Users\Bill\AppData\Local\LGHUB\settings.db"
TABLE_NAME = "DATA"
ID_COLUMN = "_id"          # Typically "1" for the row with your JSON
JSON_COLUMN = "FILE"       # BLOB that stores JSON text

# Icon cache folder for storing final .bmp images
ICON_CACHE_FOLDER = r"C:\Users\Bill\AppData\Local\LGHUB\icon_cache"

# Make sure the folder exists (optional)
if not os.path.isdir(ICON_CACHE_FOLDER):
    try:
        os.makedirs(ICON_CACHE_FOLDER)
        logging.debug(f"Created icon cache folder: {ICON_CACHE_FOLDER}")
    except Exception as e:
        logging.warning(f"Could not create icon cache folder '{ICON_CACHE_FOLDER}': {e}")

# -------------------------------------------------------------
# Data Loading / Saving
# -------------------------------------------------------------
def load_profiles_from_db(db_path):
    """
    Reads all rows from the 'DATA' table, decodes the 'FILE' BLOB as UTF-8 JSON,
    and extracts the 'applications' list. Returns a list of profiles plus references
    to the entire JSON object and the DB row ID.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    logging.debug("Connecting to DB and loading rows...")

    # Pull all rows: _id, FILE (the BLOB)
    cursor.execute(f"SELECT {ID_COLUMN}, {JSON_COLUMN} FROM {TABLE_NAME}")
    rows = cursor.fetchall()
    conn.close()

    all_profiles = []
    for (row_id, data_blob) in rows:
        logging.debug(f"Found row {row_id} in table '{TABLE_NAME}'.")
        if not data_blob:
            logging.warning(f"Row {row_id} has empty BLOB. Skipping.")
            continue

        try:
            # Decode BLOB -> string -> JSON
            json_str = data_blob.decode("utf-8")
            parsed_data = json.loads(json_str)
        except Exception as e:
            logging.warning(f"Could not parse JSON in row {row_id}: {e}")
            continue

        # Attempt to locate the "applications" list inside parsed_data
        apps_section = parsed_data.get("applications")
        if isinstance(apps_section, dict):
            apps_list = apps_section.get("applications", [])
            if isinstance(apps_list, list):
                for profile in apps_list:
                    all_profiles.append({
                        "db_row_id": row_id,
                        "entire_json": parsed_data,
                        "profile": profile
                    })

    logging.info(f"Total profiles found across all rows: {len(all_profiles)}")
    return all_profiles

def save_profile_to_db(db_path, row_id, entire_json):
    """
    Given the entire updated JSON for a single row, re-dump to string,
    encode to BLOB, and UPDATE that row in 'DATA'.
    """
    try:
        new_json_str = json.dumps(entire_json, indent=2)
        new_data_blob = new_json_str.encode("utf-8")
    except Exception as e:
        logging.error(f"Failed to encode updated JSON: {e}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        update_sql = f"UPDATE {TABLE_NAME} SET {JSON_COLUMN} = ? WHERE {ID_COLUMN} = ?"
        cursor.execute(update_sql, (new_data_blob, row_id))
        conn.commit()
        conn.close()
        logging.debug(f"Updated row {row_id} successfully.")
    except Exception as e:
        logging.error(f"Failed to write updated JSON back to DB row {row_id}: {e}")


# -------------------------------------------------------------
# GUI Class
# -------------------------------------------------------------
class GHubEditorApp:
    def __init__(self, master):
        self.master = master
        master.title("Logitech G-Hub Profile Editor (settings.db)")

        # Load all profiles
        self.profiles = load_profiles_from_db(DB_PATH)
        self.selected_profile_index = None

        # Keep a reference to the loaded icon so it doesn't get GC'd
        self.icon_tk = None

        # Layout frames
        self.left_frame = tk.Frame(master)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        self.right_frame = tk.Frame(master)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create listbox + scrollbar
        self.profile_list_var = tk.StringVar()
        self.profile_listbox = tk.Listbox(
            self.left_frame, listvariable=self.profile_list_var, width=40, height=25
        )
        self.profile_listbox.bind("<<ListboxSelect>>", self.on_profile_select)

        self.scrollbar = tk.Scrollbar(self.left_frame, orient=tk.VERTICAL)
        self.scrollbar.config(command=self.profile_listbox.yview)
        self.profile_listbox.config(yscrollcommand=self.scrollbar.set)

        self.profile_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        self.refresh_profile_list()

        # Right frame labels & entries
        label_font = ("Arial", 10, "bold")

        tk.Label(self.right_frame, text="Profile Name:", font=label_font).grid(
            row=0, column=0, sticky="e", padx=5, pady=5
        )
        self.name_entry_var = tk.StringVar()
        self.name_entry = tk.Entry(self.right_frame, textvariable=self.name_entry_var, width=50)
        self.name_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        tk.Label(self.right_frame, text="Application Path:", font=label_font).grid(
            row=1, column=0, sticky="e", padx=5, pady=5
        )
        self.app_path_var = tk.StringVar()
        self.app_path_entry = tk.Entry(self.right_frame, textvariable=self.app_path_var, width=50)
        self.app_path_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        tk.Label(self.right_frame, text="Icon (posterPath):", font=label_font).grid(
            row=2, column=0, sticky="e", padx=5, pady=5
        )
        self.icon_path_var = tk.StringVar()
        self.icon_path_entry = tk.Entry(self.right_frame, textvariable=self.icon_path_var, width=50)
        self.icon_path_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        tk.Button(self.right_frame, text="Browse Icon", command=self.browse_icon).grid(
            row=2, column=2, sticky="w", padx=5, pady=5
        )

        # Icon preview label: empty at first
        self.icon_label = tk.Label(self.right_frame, text="(No icon loaded)")
        self.icon_label.grid(row=4, column=0, columnspan=3, padx=5, pady=5)

        # Save changes button
        tk.Button(self.right_frame, text="Save Changes", command=self.save_changes).grid(
            row=5, column=0, columnspan=3, pady=10
        )

        # Let column 1 expand
        self.right_frame.grid_columnconfigure(1, weight=1)

    def refresh_profile_list(self):
        """Populate listbox with profile names."""
        profile_names = []
        for item in self.profiles:
            p_name = item["profile"].get("name", "(Unnamed)")
            profile_names.append(p_name)
        self.profile_list_var.set(profile_names)

    def on_profile_select(self, event):
        """When user selects a profile, display its details on the right."""
        try:
            selection_index = self.profile_listbox.curselection()[0]
            self.selected_profile_index = selection_index
            profile_data = self.profiles[selection_index]["profile"]

            self.name_entry_var.set(profile_data.get("name", ""))
            self.app_path_var.set(profile_data.get("applicationPath", ""))
            self.icon_path_var.set(profile_data.get("posterPath", ""))

            logging.debug(f"Selected profile index={selection_index}, name={profile_data.get('name')}")

            # Attempt to load the icon preview
            self.load_icon_preview()
        except IndexError:
            self.selected_profile_index = None

    def browse_icon(self):
        """
        Let user pick a new icon file (png/jpg/jpeg/bmp/ico),
        then convert it to BMP and save it in the icon_cache folder.
        If there's an existing posterPath, we overwrite that file.
        Otherwise, we create a new .bmp filename based on the app name.
        Finally, we set posterPath to that new file path and display preview.
        """
        new_icon_file = filedialog.askopenfilename(
            title="Select icon file",
            filetypes=[
                ("Image Files", "*.bmp;*.ico;*.png;*.jpg;*.jpeg"),
                ("All files", "*.*")
            ]
        )
        if not new_icon_file:
            return  # user canceled

        if self.selected_profile_index is None:
            messagebox.showwarning("No profile selected", "Please select a profile first.")
            return

        # Convert & copy/overwrite
        profile_data = self.profiles[self.selected_profile_index]["profile"]

        # 1) Open the chosen file with Pillow
        try:
            img = Image.open(new_icon_file)
        except Exception as e:
            logging.error(f"Failed to open image {new_icon_file}: {e}")
            messagebox.showerror("Error", f"Could not open image file:\n{e}")
            return

        # 2) Decide on output path
        existing_path = profile_data.get("posterPath", "").strip()
        app_name = profile_data.get("name", "").strip()
        if not app_name:
            app_name = "app_unknown"

        # We'll sanitize the app_name a bit for the filename (optional)
        safe_name = re.sub(r'[^\w\s-]', '', app_name)  # remove weird chars
        safe_name = safe_name.strip().replace(' ', '_') or "icon"

        if existing_path:
            # If we already had a path, we overwrite that exact file.
            # But let's forcibly ensure it ends with .bmp
            # (If the existing path isn't in icon_cache, or is .png, etc., we override anyway.)
            base, _ext = os.path.splitext(existing_path)
            final_path = base + ".bmp"
        else:
            # Create a new path in the icon cache
            final_path = os.path.join(ICON_CACHE_FOLDER, safe_name + ".bmp")

        logging.debug(f"Saving new BMP icon to: {final_path}")

        try:
            # 3) Convert & save as BMP
            # Overwrite if it already exists
            img.save(final_path, "BMP")
        except Exception as e:
            logging.error(f"Failed to save BMP to {final_path}: {e}")
            messagebox.showerror("Error", f"Could not save BMP:\n{e}")
            return

        # 4) Update the profile’s posterPath and the GUI field
        profile_data["posterPath"] = final_path
        self.icon_path_var.set(final_path)
        logging.info(f"Poster path updated to {final_path}")

        # 5) Reload preview
        self.load_icon_preview()

    def load_icon_preview(self):
        """
        Tries to open the file in self.icon_path_var and display it in self.icon_label.
        If it fails or is empty, sets label to "(No icon loaded)".
        """
        path = self.icon_path_var.get().strip()
        if not path:
            self.icon_label.config(text="(No icon loaded)", image="", compound=tk.NONE)
            return

        if not os.path.isfile(path):
            logging.warning(f"Icon file not found: {path}")
            self.icon_label.config(text="(File not found)", image="", compound=tk.NONE)
            return

        try:
            img = Image.open(path)
            # We do NOT resize (you said you'd handle resizing yourself), so full size is shown
            # But for a big file, that might blow up the UI. Up to you:
            # img = img.resize((64, 64), Image.Resampling.LANCZOS)

            self.icon_tk = ImageTk.PhotoImage(img)
            self.icon_label.config(image=self.icon_tk, text="", compound=tk.NONE)
        except Exception as e:
            logging.warning(f"Failed to load image '{path}': {e}")
            self.icon_label.config(text="(Invalid image)", image="", compound=tk.NONE)

    def save_changes(self):
        """
        Write the updated JSON back to the DB for the currently selected profile.
        """
        if self.selected_profile_index is None:
            messagebox.showwarning("No profile selected", "Select a profile first.")
            return

        new_name = self.name_entry_var.get()
        new_app_path = self.app_path_var.get()
        new_icon_path = self.icon_path_var.get()

        item = self.profiles[self.selected_profile_index]
        db_row_id = item["db_row_id"]
        entire_json = item["entire_json"]
        profile_data = item["profile"]

        profile_data["name"] = new_name
        profile_data["applicationPath"] = new_app_path
        if new_icon_path:
            profile_data["posterPath"] = new_icon_path

        # Write the entire JSON back to DB
        save_profile_to_db(DB_PATH, db_row_id, entire_json)

        # Refresh list to show new name
        self.refresh_profile_list()
        self.profile_listbox.selection_clear(0, tk.END)
        self.profile_listbox.selection_set(self.selected_profile_index)

        logging.info(f"Changes saved for profile '{new_name}' (row ID={db_row_id}).")
        messagebox.showinfo("Saved", f"Profile '{new_name}' updated in DB.")


# -------------------------------------------------------------
# Main Entry Point
# -------------------------------------------------------------
def main():
    root = tk.Tk()
    app = GHubEditorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
