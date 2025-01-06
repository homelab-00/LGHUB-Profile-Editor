#!/usr/bin/env python3
# -------------------------------------------------------------
# Logitech G-Hub Profile Editor (Extended) - Fixed
# -------------------------------------------------------------
# Fixes:
# 1) save_profile_to_db() signature matches usage
# 2) Properly copying new icons into icon_cache for profiles without an icon
# 3) Slight dark-theme improvements
# 4) Alphabetical list, add/delete entry, clear icon, etc.
#
# Logging ~7/10 for debugging

import sqlite3
import json
import os
import re
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(asctime)s - %(message)s'
)

# ---------------------------------------
# DB and Folder Config
# ---------------------------------------
DB_PATH = r"C:\Users\Bill\AppData\Local\LGHUB\settings.db"
TABLE_NAME = "DATA"
ID_COLUMN = "_id"
JSON_COLUMN = "FILE"
ICON_CACHE_FOLDER = r"C:\Users\Bill\AppData\Local\LGHUB\icon_cache"

if not os.path.isdir(ICON_CACHE_FOLDER):
    try:
        os.makedirs(ICON_CACHE_FOLDER)
    except Exception as e:
        logging.warning(f"Could not create icon cache folder: {e}")

# ---------------------------------------
# DB Helpers
# ---------------------------------------
def load_profiles_from_db(db_path):
    """
    Reads the 'DATA' table from settings.db, decodes the BLOB column as JSON,
    returns a list of dicts: { db_row_id, entire_json, profile }.
    Each 'profile' is one entry in the "applications" array.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT {ID_COLUMN}, {JSON_COLUMN} FROM {TABLE_NAME}")
    rows = cursor.fetchall()
    conn.close()

    all_profiles = []
    for (row_id, data_blob) in rows:
        if not data_blob:
            continue
        try:
            json_str = data_blob.decode("utf-8")
            parsed_data = json.loads(json_str)
        except Exception as e:
            logging.warning(f"Failed to parse JSON row {row_id}: {e}")
            continue

        apps_section = parsed_data.get("applications")
        if isinstance(apps_section, dict):
            apps_list = apps_section.get("applications", [])
            if isinstance(apps_list, list):
                for prof in apps_list:
                    all_profiles.append({
                        "db_row_id": row_id,
                        "entire_json": parsed_data,
                        "profile": prof
                    })

    # Sort them by profile "name" alphabetically
    all_profiles.sort(key=lambda p: p["profile"].get("name", "").lower())
    logging.info(f"Loaded {len(all_profiles)} profiles across all rows.")
    return all_profiles

def save_profile_to_db(db_path, row_id, entire_json):
    """
    Correct function signature: We pass 3 arguments in total:
    1) db_path
    2) row_id
    3) entire_json
    """
    try:
        new_json_str = json.dumps(entire_json, indent=2)
        new_blob = new_json_str.encode("utf-8")
    except Exception as e:
        logging.error(f"Could not encode updated JSON: {e}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        sql = f"UPDATE {TABLE_NAME} SET {JSON_COLUMN} = ? WHERE {ID_COLUMN} = ?"
        cursor.execute(sql, (new_blob, row_id))
        conn.commit()
        conn.close()
        logging.debug(f"Row {row_id} updated in DB.")
    except Exception as e:
        logging.error(f"DB update failed: {e}")

# ---------------------------------------
# Main GUI
# ---------------------------------------
class GHubEditorApp:
    def __init__(self, master):
        self.master = master
        master.title("G-Hub Profile Editor (Fixed)")

        # Minimal dark theme
        self.apply_dark_theme(master)

        # Load profiles
        self.profiles = load_profiles_from_db(DB_PATH)
        self.selected_profile_index = None
        self.icon_tk = None

        # ---- Left Frame for list ----
        self.left_frame = tk.Frame(master, bg="#2a2a2a")
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        # ---- Right Frame for details ----
        self.right_frame = ttk.Frame(master, style="Dark.TFrame")
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Listbox (with exportselection=0 to preserve selection)
        self.profile_list_var = tk.StringVar()
        self.profile_listbox = tk.Listbox(
            self.left_frame,
            listvariable=self.profile_list_var,
            width=40,
            height=25,
            exportselection=False,  # preserve selection when editing text
            bg="#2a2a2a",
            fg="#ffffff",
            selectbackground="#444444",
            highlightthickness=1,
            highlightcolor="#444444",
            bd=0
        )
        self.profile_listbox.bind("<<ListboxSelect>>", self.on_profile_select)

        # Scrollbar
        self.scrollbar = tk.Scrollbar(self.left_frame, orient=tk.VERTICAL, bg="#2a2a2a")
        self.scrollbar.config(command=self.profile_listbox.yview)
        self.profile_listbox.config(yscrollcommand=self.scrollbar.set)

        self.profile_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        # Populate list
        self.populate_list()

        # Buttons on top row
        row_idx = 0
        add_button = ttk.Button(self.right_frame, text="Add Entry", command=self.add_entry)
        add_button.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")

        del_button = ttk.Button(self.right_frame, text="Delete Entry", command=self.delete_entry)
        del_button.grid(row=row_idx, column=1, padx=5, pady=5, sticky="w")

        # Name
        row_idx += 1
        ttk.Label(self.right_frame, text="Profile Name:", style="Dark.TLabel").grid(
            row=row_idx, column=0, sticky="e", padx=5, pady=5
        )
        self.name_entry_var = tk.StringVar()
        self.name_entry = ttk.Entry(self.right_frame, textvariable=self.name_entry_var, width=50, style="Dark.TEntry")
        self.name_entry.grid(row=row_idx, column=1, sticky="w", padx=5, pady=5)

        # App Path
        row_idx += 1
        ttk.Label(self.right_frame, text="Application Path:", style="Dark.TLabel").grid(
            row=row_idx, column=0, sticky="e", padx=5, pady=5
        )
        self.app_path_var = tk.StringVar()
        self.app_path_entry = ttk.Entry(self.right_frame, textvariable=self.app_path_var, width=50, style="Dark.TEntry")
        self.app_path_entry.grid(row=row_idx, column=1, sticky="w", padx=5, pady=5)

        # Icon Path
        row_idx += 1
        ttk.Label(self.right_frame, text="Icon (posterPath):", style="Dark.TLabel").grid(
            row=row_idx, column=0, sticky="e", padx=5, pady=5
        )
        self.icon_path_var = tk.StringVar()
        self.icon_path_entry = ttk.Entry(self.right_frame, textvariable=self.icon_path_var, width=50, style="Dark.TEntry")
        self.icon_path_entry.grid(row=row_idx, column=1, sticky="w", padx=5, pady=5)

        ttk.Button(self.right_frame, text="Browse Icon", command=self.browse_icon).grid(
            row=row_idx, column=2, sticky="w", padx=5, pady=5
        )

        # Clear icon
        row_idx += 1
        clear_button = ttk.Button(self.right_frame, text="Clear Icon", command=self.clear_icon)
        clear_button.grid(row=row_idx, column=1, sticky="w", padx=5, pady=5)

        # Icon preview
        row_idx += 1
        self.icon_label = ttk.Label(self.right_frame, text="(No icon loaded)", style="Dark.TLabel")
        self.icon_label.grid(row=row_idx, column=0, columnspan=3, padx=5, pady=5)

        # Save changes
        row_idx += 1
        ttk.Button(self.right_frame, text="Save Changes", command=self.save_changes).grid(
            row=row_idx, column=0, columnspan=3, pady=10
        )

        # Let the second column expand
        self.right_frame.grid_columnconfigure(1, weight=1)

    # -----------------------------
    # Dark Theme Setup
    # -----------------------------
    def apply_dark_theme(self, root):
        style = ttk.Style(root)
        style.theme_use("clam")
        root.configure(bg="#2a2a2a")

        # Frame
        style.configure("Dark.TFrame", background="#2a2a2a")
        # Label
        style.configure("Dark.TLabel", background="#2a2a2a", foreground="#ffffff")
        # Entry
        style.configure("Dark.TEntry", fieldbackground="#444444", foreground="#ffffff")
        # Button
        style.configure("TButton", background="#444444", foreground="#ffffff")        

    # -----------------------------
    # Profile List
    # -----------------------------
    def populate_list(self):
        names = [p["profile"].get("name", "(Unnamed)") for p in self.profiles]
        self.profile_list_var.set(names)

    def on_profile_select(self, event):
        try:
            idx = self.profile_listbox.curselection()[0]
        except IndexError:
            self.selected_profile_index = None
            return

        self.selected_profile_index = idx
        item = self.profiles[idx]
        prof = item["profile"]

        self.name_entry_var.set(prof.get("name", ""))
        self.app_path_var.set(prof.get("applicationPath", ""))
        self.icon_path_var.set(prof.get("posterPath", ""))

        self.load_icon_preview()

    # -----------------------------
    # Add / Delete
    # -----------------------------
    def add_entry(self):
        if not self.profiles:
            messagebox.showinfo("No DB Rows", "No existing rows found in DB to attach a new entry.")
            return

        # Use the same row_id as the first profile found
        row_id = self.profiles[0]["db_row_id"]
        entire_json = self.profiles[0]["entire_json"]
        apps_section = entire_json.get("applications", {})
        apps_list = apps_section.get("applications", [])

        new_profile = {
            "applicationId": "new-app-id",
            "applicationPath": "",
            "isCustom": True,
            "name": "New Entry",
            "posterPath": ""
        }
        apps_list.append(new_profile)
        apps_section["applications"] = apps_list
        entire_json["applications"] = apps_section

        save_profile_to_db(DB_PATH, row_id, entire_json)

        # Reload
        self.profiles = load_profiles_from_db(DB_PATH)
        self.populate_list()

        # Auto-select
        idx = None
        for i, p in enumerate(self.profiles):
            if p["profile"].get("name") == "New Entry":
                idx = i
                break
        if idx is not None:
            self.profile_listbox.selection_clear(0, tk.END)
            self.profile_listbox.selection_set(idx)
            self.profile_listbox.event_generate("<<ListboxSelect>>")

    def delete_entry(self):
        if self.selected_profile_index is None:
            messagebox.showwarning("No selection", "Please select a profile first.")
            return

        confirm = messagebox.askyesno("Delete Entry", "Are you sure you want to delete this entry?")
        if not confirm:
            return

        item = self.profiles[self.selected_profile_index]
        row_id = item["db_row_id"]
        entire_json = item["entire_json"]
        prof_to_delete = item["profile"]

        apps_list = entire_json.get("applications", {}).get("applications", [])
        if prof_to_delete in apps_list:
            apps_list.remove(prof_to_delete)
        entire_json["applications"]["applications"] = apps_list

        save_profile_to_db(DB_PATH, row_id, entire_json)

        # Reload
        self.profiles = load_profiles_from_db(DB_PATH)
        self.selected_profile_index = None
        self.populate_list()

        # Clear fields
        self.name_entry_var.set("")
        self.app_path_var.set("")
        self.icon_path_var.set("")
        self.icon_label.config(text="(No icon loaded)", image="")

    # -----------------------------
    # Icon
    # -----------------------------
    def browse_icon(self):
        if self.selected_profile_index is None:
            messagebox.showwarning("No Profile", "Select a profile first.")
            return

        file_path = filedialog.askopenfilename(
            title="Select icon file",
            filetypes=[
                ("Image Files", "*.bmp;*.ico;*.png;*.jpg;*.jpeg"),
                ("All files", "*.*")
            ]
        )
        if not file_path:
            return

        try:
            img = Image.open(file_path)
        except Exception as e:
            logging.error(f"Failed to open image {file_path}: {e}")
            messagebox.showerror("Error", f"Could not open image file:\n{e}")
            return

        item = self.profiles[self.selected_profile_index]
        prof = item["profile"]
        existing_path = prof.get("posterPath", "").strip()
        app_name = prof.get("name", "").strip() or "app_unknown"
        safe_name = re.sub(r'[^\w\s-]', '', app_name).strip().replace(' ', '_') or "icon"

        # If there's an existing file, overwrite its base. Otherwise, create new
        if existing_path:
            base, _ext = os.path.splitext(existing_path)
            final_path = base + ".bmp"
        else:
            final_path = os.path.join(ICON_CACHE_FOLDER, safe_name + ".bmp")

        # Convert to BMP
        try:
            img.save(final_path, "BMP")
        except Exception as e:
            logging.error(f"Failed to save BMP to {final_path}: {e}")
            messagebox.showerror("Error", f"Could not save BMP:\n{e}")
            return

        prof["posterPath"] = final_path
        self.icon_path_var.set(final_path)
        self.load_icon_preview()

    def clear_icon(self):
        if self.selected_profile_index is None:
            messagebox.showwarning("No Profile", "Select a profile first.")
            return
        item = self.profiles[self.selected_profile_index]
        prof = item["profile"]
        prof["posterPath"] = ""
        self.icon_path_var.set("")
        self.icon_label.config(text="(No icon loaded)", image="", compound=tk.NONE)
        logging.info("Icon cleared. posterPath is now empty.")

    def load_icon_preview(self):
        path = self.icon_path_var.get().strip()
        if not path:
            self.icon_label.config(text="(No icon loaded)", image="", compound=tk.NONE)
            return
        if not os.path.isfile(path):
            self.icon_label.config(text="(File not found)", image="", compound=tk.NONE)
            return

        try:
            img = Image.open(path)
            self.icon_tk = ImageTk.PhotoImage(img)
            self.icon_label.config(image=self.icon_tk, text="", compound=tk.NONE)
        except Exception as e:
            logging.warning(f"Failed to load image '{path}': {e}")
            self.icon_label.config(text="(Invalid image)", image="", compound=tk.NONE)

    # -----------------------------
    # Save
    # -----------------------------
    def save_changes(self):
        if self.selected_profile_index is None:
            messagebox.showwarning("No Profile", "Select a profile first.")
            return

        item = self.profiles[self.selected_profile_index]
        row_id = item["db_row_id"]
        entire_json = item["entire_json"]
        prof = item["profile"]

        prof["name"] = self.name_entry_var.get()
        prof["applicationPath"] = self.app_path_var.get()
        prof["posterPath"] = self.icon_path_var.get()

        # Call the correct function signature
        save_profile_to_db(DB_PATH, row_id, entire_json)

        # Reload
        self.profiles = load_profiles_from_db(DB_PATH)
        self.populate_list()

        # Try to keep selection on the same name
        new_name = prof["name"]
        idx = None
        for i, p in enumerate(self.profiles):
            if p["profile"].get("name") == new_name:
                idx = i
                break
        if idx is not None:
            self.profile_listbox.selection_clear(0, tk.END)
            self.profile_listbox.selection_set(idx)
            self.profile_listbox.event_generate("<<ListboxSelect>>")

        logging.info(f"Changes saved for profile '{new_name}' (row ID={row_id}).")
        messagebox.showinfo("Saved", f"Profile '{new_name}' updated.")

# ---------------------------------------
# Main
# ---------------------------------------
def main():
    root = tk.Tk()
    app = GHubEditorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
