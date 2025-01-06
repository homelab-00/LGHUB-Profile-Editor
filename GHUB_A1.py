#!/usr/bin/env python3
# -------------------------------------------------------------
# Logitech G-Hub Profile Editor (using settings.db)
# -------------------------------------------------------------
# 1) Reads "settings.db" from "C:\\Users\\Bill\\AppData\\Local\\LGHUB"
# 2) Connects to table "DATA" and column "FILE" (BLOB) containing JSON
# 3) Decodes BLOB -> JSON, finds "applications" -> "applications" array
# 4) Lists all profiles in a Tkinter GUI, lets you rename them, change
#    application path, and poster/icon path
# 5) On Save, writes the updated JSON back into the same BLOB (encoded as bytes)
# Logging ~7/10 for debugging

import sqlite3
import json
import os
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

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
JSON_COLUMN = "FILE"       # BLOB that actually stores JSON text
ICON_CACHE_FOLDER = r"C:\Users\Bill\AppData\Local\LGHUB\icon_cache"

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
        # Typically: parsed_data["applications"]["applications"] is your profiles array
        apps_list = None
        if isinstance(parsed_data, dict):
            apps_section = parsed_data.get("applications")
            if isinstance(apps_section, dict):
                apps_list = apps_section.get("applications")

        # If found, iterate the list to store each item, along with references
        if apps_list and isinstance(apps_list, list):
            for profile in apps_list:
                all_profiles.append({
                    "db_row_id": row_id,       # which DB row it came from
                    "entire_json": parsed_data,# the entire JSON structure
                    "profile": profile         # the "application" dict
                })
        else:
            logging.debug(f"Row {row_id} has no 'applications' list. Skipping.")

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
        tk.Entry(self.right_frame, textvariable=self.name_entry_var, width=50).grid(
            row=0, column=1, sticky="w", padx=5, pady=5
        )

        tk.Label(self.right_frame, text="Application Path:", font=label_font).grid(
            row=1, column=0, sticky="e", padx=5, pady=5
        )
        self.app_path_var = tk.StringVar()
        tk.Entry(self.right_frame, textvariable=self.app_path_var, width=50).grid(
            row=1, column=1, sticky="w", padx=5, pady=5
        )

        tk.Label(self.right_frame, text="Icon (posterPath):", font=label_font).grid(
            row=2, column=0, sticky="e", padx=5, pady=5
        )
        self.icon_path_var = tk.StringVar()
        tk.Entry(self.right_frame, textvariable=self.icon_path_var, width=50).grid(
            row=2, column=1, sticky="w", padx=5, pady=5
        )

        tk.Button(self.right_frame, text="Browse Icon", command=self.browse_icon).grid(
            row=2, column=2, sticky="w", padx=5, pady=5
        )

        tk.Button(self.right_frame, text="Save Changes", command=self.save_changes).grid(
            row=3, column=0, columnspan=3, pady=10
        )

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
        except IndexError:
            self.selected_profile_index = None

    def browse_icon(self):
        """Let user pick a new icon file, then set it in the icon_path_var."""
        new_icon_file = filedialog.askopenfilename(
            title="Select icon file",
            filetypes=[
                ("Bitmap Images", "*.bmp"),
                ("Icon Files", "*.ico"),
                ("PNG Images", "*.png"),
                ("All files", "*.*")
            ]
        )
        if new_icon_file:
            self.icon_path_var.set(new_icon_file)
            logging.debug(f"User selected new icon: {new_icon_file}")

    def save_changes(self):
        """Save the updated name/app_path/icon_path back to the DB."""
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

        save_profile_to_db(DB_PATH, db_row_id, entire_json)

        # Refresh the list to show the updated name
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
