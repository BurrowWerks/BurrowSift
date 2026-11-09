import exceptions
import os
from pathlib import Path
from typing import Any
from pypdf import PdfReader
from docx import Document

def read_content(file_data_path: str) -> str:
    if not Path(file_data_path).is_file():
        raise exceptions.InvalidFileError()
    if not os.access(path=file_data_path, mode=os.R_OK):
        raise exceptions.FileNotReadableError()
    file_extension: str = Path(file_data_path).suffix.lower()

    if file_extension == '.pdf':
        return read_pdf_content(file_data_path)

    if file_extension == '.docx':
        return read_docx_content(file_data_path)

    if file_extension == '.txt':
        return read_txt_content(file_data_path)

    raise exceptions.InvalidFileTypeError()

def read_pdf_content(file_data_path: str) -> str:
    if not Path(file_data_path).is_file():
        raise exceptions.InvalidFileError()
    if not os.access(path=file_data_path, mode=os.R_OK):
        raise exceptions.FileNotReadableError()
    read_pdf: Any = PdfReader(stream=file_data_path)
    pdf_content: list[str] = []
    for page in read_pdf.pages:
        page_text: str = page.extract_text() or ""
        pdf_content.append(page_text)
    return "\n".join(pdf_content)

def read_docx_content(file_data_path: str) -> str:
    if not Path(file_data_path).is_file():
        raise exceptions.InvalidFileError()
    if not os.access(path=file_data_path, mode=os.R_OK):
        raise exceptions.FileNotReadableError()
    document: Any = Document(docx=file_data_path)
    docx_content: list[str] = []
    for paragraph in document.paragraphs:
        docx_content.append(paragraph.text)
    return "\n\n".join(docx_content)

def read_txt_content(file_data_path: str) -> str:
    if not Path(file_data_path).is_file():
        raise exceptions.InvalidFileError()
    if not os.access(path=file_data_path, mode=os.R_OK):
        raise exceptions.FileNotReadableError()
    with open(file=file_data_path, mode='r', encoding='utf-8') as text_file:
        text_content: str = text_file.read()
    return text_content