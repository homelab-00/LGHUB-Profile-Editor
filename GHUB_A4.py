#!/usr/bin/env python3
# -------------------------------------------------------------
# Logitech G-Hub Profile Editor (settings.db) - Extended
# -------------------------------------------------------------
# Features added:
# 1) Alphabetical list of profiles
# 2) Dark-themed UI
# 3) List selection is preserved while editing text fields
# 4) "Clear Icon" button
# 5) "Delete Entry" button
# 6) "Add Entry" button
# 7) Icon copying/conversion into icon_cache folder
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
def load_profiles_from_db():
    """
    Reads the 'DATA' table from settings.db, decodes the BLOB column as JSON,
    returns a list of dicts: { db_row_id, entire_json, profile }.
    Each 'profile' is one entry in the "applications" array.
    """
    conn = sqlite3.connect(DB_PATH)
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

    # We’ll sort them by profile "name" right here
    all_profiles.sort(key=lambda p: p["profile"].get("name", "").lower())

    logging.info(f"Loaded {len(all_profiles)} profiles across all rows.")
    return all_profiles

def save_profile_to_db(row_id, entire_json):
    """Takes the updated JSON, encodes to bytes, and writes back to the DB."""
    try:
        new_json_str = json.dumps(entire_json, indent=2)
        new_blob = new_json_str.encode("utf-8")
    except Exception as e:
        logging.error(f"Could not encode updated JSON: {e}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
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
        master.title("G-Hub Profile Editor (Extended)")

        # Apply a minimal dark theme style
        self.apply_dark_theme(master)

        self.profiles = load_profiles_from_db()
        self.selected_profile_index = None
        self.icon_tk = None

        # ---- Left Frame for list ----
        self.left_frame = tk.Frame(master)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        # ---- Right Frame for details ----
        self.right_frame = tk.Frame(master)
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
            highlightthickness=0,
            borderwidth=0
        )
        self.profile_listbox.bind("<<ListboxSelect>>", self.on_profile_select)

        # Scrollbar
        self.scrollbar = tk.Scrollbar(self.left_frame, orient=tk.VERTICAL, bg="#2a2a2a")
        self.scrollbar.config(command=self.profile_listbox.yview)
        self.profile_listbox.config(yscrollcommand=self.scrollbar.set)

        self.profile_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        self.populate_list()

        # -- Right Frame Widgets --

        row_idx = 0
        self.label_font = ("Arial", 10, "bold")

        # Buttons for "Add" & "Delete"
        add_button = ttk.Button(self.right_frame, text="Add Entry", command=self.add_entry)
        add_button.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")

        del_button = ttk.Button(self.right_frame, text="Delete Entry", command=self.delete_entry)
        del_button.grid(row=row_idx, column=1, padx=5, pady=5, sticky="w")

        row_idx += 1
        ttk.Label(self.right_frame, text="Profile Name:", style="Dark.TLabel").grid(
            row=row_idx, column=0, sticky="e", padx=5, pady=5
        )
        self.name_entry_var = tk.StringVar()
        self.name_entry = ttk.Entry(self.right_frame, textvariable=self.name_entry_var, width=50)
        self.name_entry.grid(row=row_idx, column=1, sticky="w", padx=5, pady=5)

        row_idx += 1
        ttk.Label(self.right_frame, text="Application Path:", style="Dark.TLabel").grid(
            row=row_idx, column=0, sticky="e", padx=5, pady=5
        )
        self.app_path_var = tk.StringVar()
        self.app_path_entry = ttk.Entry(self.right_frame, textvariable=self.app_path_var, width=50)
        self.app_path_entry.grid(row=row_idx, column=1, sticky="w", padx=5, pady=5)

        row_idx += 1
        ttk.Label(self.right_frame, text="Icon (posterPath):", style="Dark.TLabel").grid(
            row=row_idx, column=0, sticky="e", padx=5, pady=5
        )
        self.icon_path_var = tk.StringVar()
        self.icon_path_entry = ttk.Entry(self.right_frame, textvariable=self.icon_path_var, width=50)
        self.icon_path_entry.grid(row=row_idx, column=1, sticky="w", padx=5, pady=5)

        ttk.Button(self.right_frame, text="Browse Icon", command=self.browse_icon).grid(
            row=row_idx, column=2, sticky="w", padx=5, pady=5
        )

        row_idx += 1
        # Clear icon button
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
    # Theming
    # -----------------------------
    def apply_dark_theme(self, root):
        """Apply a minimal dark theme using ttk.Style and manual config for the root."""
        style = ttk.Style(root)
        # You can try 'clam', 'alt', 'default', etc.
        style.theme_use("clam")

        # Frame background
        root.configure(bg="#2a2a2a")

        # TLabel, TEntry, TButton, etc.
        style.configure("Dark.TLabel", background="#2a2a2a", foreground="#ffffff")
        style.configure("TFrame", background="#2a2a2a")
        style.configure("TButton", background="#444444", foreground="#ffffff")
        style.configure("TEntry", fieldbackground="#444444", foreground="#ffffff")

    # -----------------------------
    # Profile List Handling
    # -----------------------------
    def populate_list(self):
        """Populate the listbox with the sorted profile names."""
        # We assume self.profiles is already sorted
        names = [p["profile"].get("name", "(Unnamed)") for p in self.profiles]
        self.profile_list_var.set(names)

    def on_profile_select(self, event):
        """When user selects a profile from the list, load its details on the right."""
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
        """Create a new blank entry in the JSON, store to DB, refresh list."""
        if not self.profiles:
            messagebox.showinfo("No DB Rows", "No existing rows found in DB to attach a new entry.")
            return

        # We can just add it to the same row_id as the first entry
        row_id = self.profiles[0]["db_row_id"]
        entire_json = self.profiles[0]["entire_json"]
        applications = entire_json.get("applications", {})
        apps_list = applications.get("applications", [])

        # Minimal new entry
        new_profile = {
            "applicationId": "new-app-id",
            "applicationPath": "",
            "isCustom": True,
            "name": "New Entry",
            "posterPath": ""
        }

        apps_list.append(new_profile)
        applications["applications"] = apps_list
        entire_json["applications"] = applications

        # Save changes to DB
        save_profile_to_db(DB_PATH, row_id, entire_json)

        # Reload everything from DB
        self.profiles = load_profiles_from_db()
        self.populate_list()

        # Optionally auto-select the newly added entry
        # We look for the entry with the name "New Entry"
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
        """Remove the selected entry from the JSON, save to DB."""
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

        # Remove 'prof_to_delete' from apps_list
        if prof_to_delete in apps_list:
            apps_list.remove(prof_to_delete)

        entire_json["applications"]["applications"] = apps_list
        save_profile_to_db(DB_PATH, row_id, entire_json)

        # Now reload, refresh
        self.profiles = load_profiles_from_db()
        self.selected_profile_index = None
        self.populate_list()
        # Clear the fields
        self.name_entry_var.set("")
        self.app_path_var.set("")
        self.icon_path_var.set("")
        self.icon_label.config(text="(No icon loaded)", image="")

    # -----------------------------
    # Icon Handling
    # -----------------------------
    def browse_icon(self):
        """
        Let user pick a new icon file (png/jpg/jpeg/bmp/ico),
        then convert it to BMP and save to icon_cache.
        Overwrite existing if present, else create new.
        """
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
            return  # user canceled

        # Attempt to open
        try:
            img = Image.open(file_path)
        except Exception as e:
            logging.error(f"Failed to open image {file_path}: {e}")
            messagebox.showerror("Error", f"Could not open image file:\n{e}")
            return

        item = self.profiles[self.selected_profile_index]
        profile_data = item["profile"]
        existing_path = profile_data.get("posterPath", "").strip()
        app_name = profile_data.get("name", "").strip() or "app_unknown"
        safe_name = re.sub(r'[^\w\s-]', '', app_name).strip().replace(' ', '_') or "icon"

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

        # Update JSON
        profile_data["posterPath"] = final_path
        self.icon_path_var.set(final_path)

        # Show preview
        self.load_icon_preview()

    def clear_icon(self):
        """Clear the icon from the selected profile (set posterPath to "")."""
        if self.selected_profile_index is None:
            messagebox.showwarning("No Profile", "Select a profile first.")
            return

        item = self.profiles[self.selected_profile_index]
        profile_data = item["profile"]
        profile_data["posterPath"] = ""
        self.icon_path_var.set("")

        self.icon_label.config(text="(No icon loaded)", image="", compound=tk.NONE)
        logging.info("Icon cleared. posterPath is now empty.")

    def load_icon_preview(self):
        """Load the icon from posterPath and display. No resizing by default."""
        path = self.icon_path_var.get().strip()
        if not path:
            self.icon_label.config(text="(No icon loaded)", image="", compound=tk.NONE)
            return
        if not os.path.isfile(path):
            self.icon_label.config(text="(File not found)", image="", compound=tk.NONE)
            return

        try:
            img = Image.open(path)
            # If you want a small thumbnail, you could do:
            # img = img.resize((64, 64), Image.Resampling.LANCZOS)

            self.icon_tk = ImageTk.PhotoImage(img)
            self.icon_label.config(image=self.icon_tk, text="", compound=tk.NONE)
        except Exception as e:
            logging.warning(f"Failed to load image '{path}': {e}")
            self.icon_label.config(text="(Invalid image)", image="", compound=tk.NONE)

    # -----------------------------
    # Saving
    # -----------------------------
    def save_changes(self):
        """Write the updated name/path/icon to DB for the selected entry."""
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

        # Write to DB
        save_profile_to_db(DB_PATH, row_id, entire_json)

        # Reload and keep sorted
        self.profiles = load_profiles_from_db()
        self.populate_list()

        # Attempt to find same profile by name (in case name changed)
        new_name = prof["name"]
        # We can't just do a perfect match on name if duplicates exist.
        # We'll do best effort to find first match with new_name
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
