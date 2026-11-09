from typing import Any
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import os
import json
import exceptions

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

    with open(file=auto_file_name, mode='w', encoding='utf-8') as json_file:
        json.dump(obj=final_record, fp=json_file, indent=4)

    return auto_file_name