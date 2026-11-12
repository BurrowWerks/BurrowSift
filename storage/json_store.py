from typing import Any, Type
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import os
import json
import exceptions
import tempfile

def write_content_to_json(structured_dict: dict[str, Any]) -> None:
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    output_path: str = filedialog.asksaveasfilename(title="Save JSON file", defaultextension=".json", filetypes=[("JSON files", "*.json")])

    root.destroy()  # Close the Tkinter window

    if not output_path:
        return  # User canceled the save dialog
    if not os.access(path=os.path.dirname(output_path), mode=os.W_OK):
        raise exceptions.DirectoryNotWritableError()   

    with open(file=output_path, mode='w', encoding='utf-8') as json_file:
        json.dump(obj=structured_dict, fp=json_file, indent=4)

def write_ollama_response_to_json(temp_file: str, response_dict: dict[str, Any]) -> None:
    if not os.access(path=os.path.dirname(temp_file), mode=os.W_OK):
        raise exceptions.DirectoryNotWritableError()

    with open(file=temp_file, mode='w', encoding='utf-8') as json_file:
        json.dump(obj=response_dict, fp=json_file, indent=4)


def write_final_record_to_json(final_record: dict[str, Any], auto_file_name: Path) -> Path:
    if not os.access(path=os.path.dirname(p=auto_file_name), mode=os.W_OK):
        raise exceptions.DirectoryNotWritableError()   

    atomic_write_to_json(final_file=auto_file_name, data=final_record)

    return auto_file_name

def atomic_write_to_json(final_file: Path, data: dict[str, Any]) -> None:
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, dir=final_file.parent) as temp_file:
            temp_path = temp_file.name
            json.dump(obj=data, fp=temp_file, indent=4)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, final_file)
    finally:
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError as e:
            print("Failed to remove temporary file:", e)
        