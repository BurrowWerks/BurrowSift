from os import stat_result
import sys
from tkinter import filedialog
import tkinter as tk
from pathlib import Path
from pypdf import PdfReader
from docx import Document
import json
from typing import Any
import os
from urllib import response
import requests
from requests.exceptions import RequestException


def request_document() -> str:
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    file_path: str = filedialog.askopenfilename(title="Select a document file", filetypes=[("Document files", "*.pdf *.docx *.txt")])


    root.destroy()  # Close the Tkinter window

    if file_path:
        print(f"Selected file: {file_path}")
        if not file_path.lower().endswith(('.pdf', '.docx', '.txt')):
            raise ValueError("Invalid file type. Please select a document file of types PDF, DOCX, or TXT.")
        elif not Path(file_path).is_file():
            raise FileNotFoundError("The selected file is not valid. Please select a document file of types PDF, DOCX, or TXT.")
        return file_path
    else:
        sys.exit("No file selected. Exiting the program.")
    

def read_metadata(file_path: str) -> dict[str, Any]:
    if not Path(file_path).is_file(): 
        raise FileNotFoundError("The selected file is not valid. Please select a document file of types PDF, DOCX, or TXT.")
    file_data_path = Path(file_path)
    file_data_stat: stat_result = file_data_path.stat()
    metadata: dict[str, Any] = {"file_name": file_data_path.name,
                                "file_size": file_data_stat.st_size,
                                "file_type": file_data_path.suffix,
                                "last_modified": file_data_stat.st_mtime,
                                "created": file_data_stat.st_birthtime,
                                "absolute_path": str(object=file_data_path.resolve())}
    return metadata

def read_content(file_data_path: str) -> str:
    if not Path(file_data_path).is_file():
        raise FileNotFoundError("The selected file is not valid. Please select a document file of types PDF, DOCX, or TXT.")
    if not os.access(path=file_data_path, mode=os.R_OK):
        raise PermissionError("The selected file is not readable. Please select a different file.")
    file_extension: str = Path(file_data_path).suffix.lower()

    if file_extension == '.pdf':
        return read_pdf_content(file_data_path)

    if file_extension == '.docx':
        return read_docx_content(file_data_path)

    if file_extension == '.txt':
        return read_txt_content(file_data_path)

    raise ValueError(f"Unsupported file type: {file_extension}. Please select a PDF, DOCX, or TXT file.")

def read_pdf_content(file_data_path: str) -> str:
    if not Path(file_data_path).is_file():
        raise FileNotFoundError("The selected file is not valid. Please select a document file of types PDF, DOCX, or TXT.")
    if not os.access(path=file_data_path, mode=os.R_OK):
        raise PermissionError("The selected file is not readable. Please select a different file.")
    read_pdf: Any = PdfReader(stream=file_data_path)
    pdf_content: list[str] = []
    for page in read_pdf.pages:
        page_text: str = page.extract_text() or ""
        pdf_content.append(page_text)
    return "\n".join(pdf_content)

def read_docx_content(file_data_path: str) -> str:
    if not Path(file_data_path).is_file():
        raise FileNotFoundError("The selected file is not valid. Please select a document file of types PDF, DOCX, or TXT.")
    if not os.access(path=file_data_path, mode=os.R_OK):
        raise PermissionError("The selected file is not readable. Please select a different file.")
    document: Any = Document(docx=file_data_path)
    docx_content: list[str] = []
    for paragraph in document.paragraphs:
        docx_content.append(paragraph.text)
    return "\n\n".join(docx_content)

def read_txt_content(file_data_path: str) -> str:
    if not Path(file_data_path).is_file():
        raise FileNotFoundError("The selected file is not valid. Please select a document file of types PDF, DOCX, or TXT.")
    if not os.access(path=file_data_path, mode=os.R_OK):
        raise PermissionError("The selected file is not readable. Please select a different file.")
    with open(file=file_data_path, mode='r', encoding='utf-8') as text_file:
        text_content: str = text_file.read()
    return text_content

def build_structured_content(metadata: dict[str, Any], content: str) -> dict[str, Any]:
    structured_dict: dict[str, dict[str, Any]] = {"metadata": metadata, 
                                                  "doc_content": {"content": content
                                                                  }}
    return structured_dict

def write_content_to_json(structured_dict: dict[str, Any]) -> None:
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    output_path: str = filedialog.asksaveasfilename(title="Save JSON file", defaultextension=".json", filetypes=[("JSON files", "*.json")])

    root.destroy()  # Close the Tkinter window

    if not output_path:
        return  # User canceled the save dialog
    if not os.access(path=os.path.dirname(output_path), mode=os.W_OK):
        raise PermissionError("The selected directory is not writable. Please select a different location.")

    with open(file=output_path, mode='w', encoding='utf-8') as json_file:
        json.dump(obj=structured_dict, fp=json_file, indent=4)

def send_to_ollama_api(structured_dict: dict[str, Any]) -> None:
    url = "http://localhost:11434/api/generate"

    structured_dict_json = json.dumps(structured_dict, indent=4)

    payload_category_summary = {
        "model": "gemma4:12b",
        "prompt": f"Summarise and categorise the supplied document {structured_dict_json} Provide response in JSON format with the following keys: 'category', 'summary', 'subcategories'."
        "The 'category' should be a single word that best describes the main topic of the input text for filing purposes. The 'summary' should be a concise summary of the input text, capturing the key points and main ideas. The 'subcategories' should be single words that provide a more specific classification within the main category." 
        "Ensure that the JSON response is well-structured and adheres to proper JSON formatting standards.",
        "stream": False,
    }

    response_category_summary = requests.post(url, json=payload_category_summary, timeout=(10, 300))

    if response_category_summary.status_code == 200:
        print(response_category_summary.json()["response"])  
    else:
        raise RequestException(f"Error: {response_category_summary.status_code} - {response_category_summary.text}")



def error_helper(error: ValueError | FileNotFoundError | PermissionError | RequestException) -> None:
    PermissionError_1 = "The selected file is not readable. Please select a different file."
    PermissionError_2 = "The selected directory is not writable. Please select a different location."
    if isinstance(error, ValueError):
        print("Invalid file type. Please select a document file of types PDF, DOCX, or TXT.")
    elif isinstance(error, FileNotFoundError):
        print("The selected file is not valid. Please select a document file of types PDF, DOCX, or TXT.")
    elif isinstance(error, RequestException):
        print("Error occurred while communicating with the Ollama API.")
    else:
        if "not readable" in str(error):
            print(PermissionError_1)
        else:
            print(PermissionError_2)

def main() -> None:
    while True:
        try:
            file_path: str = request_document()
        except (ValueError, FileNotFoundError, PermissionError) as error:
            error_helper(error)
            continue  # Prompt the user to select a file again
        try:
            metadata: dict[str, Any] = read_metadata(file_path)
            content: str = read_content(file_data_path=file_path)
        except (ValueError, FileNotFoundError, PermissionError) as error:
            error_helper(error)
            continue  # Prompt the user to select a file again
        structured_content: dict[str, Any] = build_structured_content(metadata, content)
        while True:
            try:
                write_content_to_json(structured_dict=structured_content)
                
            except (ValueError, FileNotFoundError, PermissionError) as error:
                error_helper(error)
                continue  # Prompt the user to select a folder again
            break  # Exit the inner loop if no exception occurs
        while True:
            try:
                send_to_ollama_api(structured_dict=structured_content)
            except (RequestException) as error:
                error_helper(error)
                continue  # Prompt the user to select a file again
            break  # Exit the inner loop if no exception occurs
        print(f"Metadata: {metadata}")
        print(f"Content preview: {content[:100] if content else 'No content'}")
        break  # Exit the loop if no exception occurs

if __name__ == "__main__":
    main()


