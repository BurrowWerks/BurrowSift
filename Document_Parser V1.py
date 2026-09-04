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
    read_pdf = PdfReader(stream=file_data_path)
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
    document = Document(docx=file_data_path)
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


def error_helper(error: ValueError | FileNotFoundError | PermissionError) -> None:
    PermissionError_1 = "The selected file is not readable. Please select a different file."
    PermissionError_2 = "The selected directory is not writable. Please select a different location."
    if isinstance(error, ValueError):
        print("Invalid file type. Please select a document file of types PDF, DOCX, or TXT.")
    elif isinstance(error, FileNotFoundError):
        print("The selected file is not valid. Please select a document file of types PDF, DOCX, or TXT.")
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
        print(f"Metadata: {metadata}")
        print(f"Content preview: {content[:100] if content else 'No content'}")
        break  # Exit the loop if no exception occurs

if __name__ == "__main__":
    main()


#TODO: whitespace normalization for the docx
#DOCUMENT PARSER - REVIEW NOTES

#(1. Fix FileNotFoundError message
#   - If Path(file_path).is_file() returns False, a path was still selected.
#   - The error should say that the selected file could not be found or is not a valid file.
#   - Do not say "No file was selected" because that represents a different state.)
#
#2. Combined exception handling
#   - Multiple exception types can be handled in the same except block using a tuple.
#   - Example:
#     except (ValueError, FileNotFoundError, PermissionError) as error:
#   - This is appropriate when both exceptions should result in the same recovery behaviour.
#
#3. Additional file-processing exceptions
#   - A file may disappear or become inaccessible after it has been selected.
#   - read_metadata() can potentially raise FileNotFoundError.
#   - File-reading operations can potentially raise PermissionError.
#   - Decide whether these errors should return the user to document selection rather than crash the program.
#
#4. Validation in request_document() and read_content()
#   - request_document() validates the user/GUI workflow.
#   - read_content() validates its own function input.
#   - Keeping validation in read_content() means it remains safe if it is called from somewhere other than request_document().
#   - This is defensive programming rather than unnecessary duplication.
#
#5. File readers can use different implementations
#   - PDF:
#     Extract text page-by-page.
#     Store page text in list[str].
#     Join pages together.
#
#   - DOCX:
#     Extract paragraph text.
#     Store paragraphs in list[str].
#     Join paragraphs using "\n\n".
#
#   - TXT:
#     Plain text already contains its own whitespace structure.
#     Use text_file.read() directly.
#
#   - All three functions share the same external contract:
#     Input = file path.
#     Output = document content as str.
#   - Their internal implementations do not need to be identical.
#
#6. DOCX whitespace normalization
#   - Empty DOCX paragraphs can create excessive blank lines.
#   - Leave whitespace normalization as a TODO for now.
#   - Test several DOCX files before deciding what whitespace should be removed.
#   - Avoid accidentally deleting meaningful document structure.
#
#7. Type annotations / function contracts
#   - request_document() -> str
#   - read_metadata() -> dict[str, Any]
#   - read_content() -> str
#   - read_pdf_content() -> str
#   - read_docx_content() -> str
#   - read_txt_content() -> str
#   - build_structured_content() -> dict[str, Any]
#   - write_content_to_json() -> None
#   - main() -> None

#   - Type annotations make the expected input/output contract of each function clearer.
#
#8. Failure-path testing
#   Test the following deliberately:
#
#   - Valid PDF
#   - Valid DOCX
#   - Valid TXT
#   - Cancel document selection
#   - Cancel JSON save
#   - Unsupported file extension
#   - File deleted/moved after selection
#   - File without read permission
#   - Empty document
#   - PDF containing no extractable text
#
#9. Behavioural testing
#   - The project is moving beyond:
#     "Does the program run?"
#
#   - Start asking:
#     "Does the program behave correctly under different states?"
#
#   - Important concepts now being introduced:
#     Error recovery
#     Exception handling
#     Exception boundaries
#     Defensive programming
#     Retry loops
#     Function contracts
#     Format-specific parsing
#     Serialization