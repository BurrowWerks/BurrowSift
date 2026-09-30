from os import stat_result
import sys
from tkinter import filedialog
import tkinter as tk
from pathlib import Path
from pypdf import PdfReader
from transformers import AutoTokenizer, PreTrainedTokenizerBase
from docx import Document
import json
from typing import Any, cast
import os
import time
import requests
from requests.exceptions import RequestException
from uuid import uuid4
import subprocess
import shutil
import sqlite3
from datetime import datetime
import duckdb


class InvalidFileTypeError(ValueError):
    statement: str = ("Invalid file type. Please select a document file of types PDF, DOCX, or TXT.")
    def __init__(self) -> None:
            super().__init__(self.statement)
class DocumentTooLargeError(ValueError):
    statement: str = ("The document exceeds the maximum supported token limit. Please select a smaller document.")
    def __init__(self) -> None:
            super().__init__(self.statement)
class InvalidFileError(FileNotFoundError):
    statement: str = ("The selected file is not valid. Please select a document file of types PDF, DOCX, or TXT.")
    def __init__(self):
            super().__init__(self.statement)
class FileNotReadableError(PermissionError):
    statement: str = ("The selected file is not readable. Please select a different file.")
    def __init__(self) -> None:
            super().__init__(self.statement)

class OriginalFileNotFoundError(FileNotFoundError):
    statement: str = ("Original file not found in staged pair.")
    def __init__(self) -> None:
                super().__init__(self.statement)

class JSONFileNotFoundError(FileNotFoundError):
    statement: str = ("JSON file not found in staged pair.")
    def __init__(self) -> None:
                super().__init__(self.statement)

class DirectoryNotWritableError(PermissionError):
    statement = ("The selected directory is not writable. Please select a different directory.")
    def __init__(self):
            super().__init__(self.statement)

class DirectoryNotReadableError(PermissionError):
    statement: str = ("The selected directory is not readable. Please select a different directory.")
    def __init__(self) -> None:
            super().__init__(self.statement)

class OllamaAPIError(RequestException):
    statement: str = ("Error occurred while communicating with the Ollama API.")
    def __init__(self) -> None:
            super().__init__(self.statement)

class OllamaResponseError(ValueError):
    statement: str = ("Error occurred while processing the Ollama API response.")
    
    def __init__(self) -> None:
        super().__init__(self.statement)

class OllamaResponseDecodingError(OllamaResponseError):
    statement: str = ("Error occurred while decoding the Ollama API response.")

class OllamaResponseFormatError(OllamaResponseError):
    statement: str = ("Error occurred due to an unexpected format in the Ollama API response.")

class StagedPairNotFoundError(KeyError):
    statement: str = ("Staged pair could not be found for the provided document ID")

    def __init__(self) -> None:
            super().__init__(self.statement)

class OriginalFileSortError(Exception):
    statement: str = ("Original file could not be moved to the sorting destination.")

    def __init__(self) -> None:
            super().__init__(self.statement)

class JSONFileSortError(Exception):
    statement: str = ("JSON file could not be moved to the sorting destination.")
    
    def __init__(self):
            super().__init__(self.statement)

class FileSortRollbackError(Exception):
    statement = ("JSON file could not be moved to the sorting destination and the original file rollback failed.")

    def __init__(self):
            super().__init__(self.statement)

class DatabaseCreationError(Exception): # Name needs changing later as this is poth creation not db creation
    statement: str = ("database creation failed")

    def __init__(self): 
        super().__init__(self.statement)
class DatabaseConnectionError(Exception): 
    statement: str = ("connection to database failed")

    def __init__(self):
            super().__init__(self.statement)
class DatabaseTableCreationError(Exception):
    statement: str = ("database table could not be created or retrieved.")

    def __init__(self):
            super().__init__(self.statement)
class DatabaseInsertionError(Exception):
    statement: str = ("Dictionary failed to pass into database")
    
    def __init__(self):
        super().__init__(self.statement)

class DuckDBDatabaseConnectionError(Exception): 
    statement: str = ("connection to database failed")

    def __init__(self):
            super().__init__(self.statement)

class DatabaseTableAlterError(Exception):
    statement: str = ("database table could not be Altered.")

    def __init__(self):
            super().__init__(self.statement)

class NoUUIDMatch(Exception):
    statement: str = ("No UUID match was found in database.")

    def __init__(self):
            super().__init__(self.statement)
          

tokenizer: PreTrainedTokenizerBase = cast(
    PreTrainedTokenizerBase,
    AutoTokenizer.from_pretrained(# pyright: ignore[reportUnknownMemberType]
        pretrained_model_name_or_path="google/gemma-4-12B"
    ),
)

def automatic_ollama_start() -> None:
    try:
        response: requests.Response = requests.get(url="http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("Ollama API is already running.")
            return
    except RequestException:
        pass  # Ollama API is not running, proceed to start it

    try:
        ollama_env = os.environ.copy()
        ollama_env["OLLAMA_FLASH_ATTENTION"] = "1"
        ollama_env["OLLAMA_KV_CACHE_TYPE"] = "q8_0"

        subprocess.Popen(args=["ollama", "serve"], env=ollama_env,)
        
        for _ in range(10):  # Poll up to 10 times
            try:
                polling_response = requests.get("http://localhost:11434/api/tags", timeout=1)
                if polling_response.status_code == 200:
                    print("Ollama API started successfully.")
                    return  # Ollama API is now running
            except RequestException:
                pass  # Continue polling
            time.sleep(1)  # Wait for 1 second before the next poll
        raise OllamaAPIError()
    except OllamaAPIError:
        raise 
    except Exception as e:
        raise OllamaAPIError() from e

def create_or_open_database() -> Path:
    try:
        data_base_dir: Path= Path(r"B:\BurrowSift\Database")
        data_base_dir.mkdir(parents=True, exist_ok=True)
        data_base_path: Path = data_base_dir/"burrowsift.db"
    except (OSError) as e:
        raise DatabaseCreationError() from e
    return data_base_path

def connect_sqlite(data_base_path: Path) -> sqlite3.Connection:
    try:
        db_connect: sqlite3.Connection = sqlite3.connect(data_base_path)
    except (sqlite3.Error) as e:
        raise DatabaseConnectionError() from e
    return db_connect

def create_db_table(db_connect:sqlite3.Connection) -> None:
    try:
        cursor = db_connect.cursor()
        schema_query = """
            CREATE TABLE IF NOT EXISTS documents(
            document_identifier TEXT PRIMARY KEY,
            source_file_name TEXT NOT NULL,
            original_file_path TEXT NOT NULL,
            current_file_path TEXT NOT NULL,
            json_file_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT NOT NULL,
            summary_text TEXT NOT NULL,
            processed_at TEXT NOT NULL)
            """
        cursor.execute(schema_query)
        db_connect.commit()
    except (sqlite3.Error) as e:
        raise DatabaseTableCreationError() from e

def alter_update_sqlite_table(db_connect: sqlite3.Connection)-> None:
    try:
        new_columns ={
            "model_name_version": "TEXT",
            "processing_duration": "REAL",
            "inference_duration_seconds": "REAL",
            "success_failure_status": "TEXT",
            "retry_count": "INTEGER",
            "chunk_count": "INTEGER",
            "processing_location": "TEXT",
            "character_count": "INTEGER", 
            "word_count": "INTEGER",
            "tokenizer_token_count": "INTEGER",
            "tokens_prompt": "INTEGER",
            "prompt_eval_count": "INTEGER",
            "eval_count": "INTEGER",
            "total_ollama_api_processing_duration": "REAL",
            "prompt_eval_duration": "INTEGER",
            "prompt_eval_duration_seconds": "REAL",
            "max_ai_config_context_window_tokens": "INTEGER",
            "max_burrowsift_processing_tokens_ceiling": "INTEGER",


        }
        table = "documents"
        cursor = db_connect.cursor()
        cursor.execute("SELECT * FROM pragma_table_info(?)",(table,))
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]


        for name, value in new_columns.items():
            if name not in column_names:
                schema_query = f"""ALTER TABLE documents ADD COLUMN {name} {value};"""
                cursor.execute(schema_query)
        db_connect.commit()
           
    except (sqlite3.Error) as e:
        db_connect.rollback()
        raise DatabaseTableAlterError() from e


def create_or_open_duckdb_path()-> Path:
    try:
        duckdb_dirs: Path = Path(r"B:\BurrowSift\Database")
        duckdb_dirs.mkdir(parents=True, exist_ok=True)
        duckdb_path: Path = duckdb_dirs/"burrowsift.analytics.duckdb"
    except (OSError) as e:
        raise DatabaseCreationError() from e
    return duckdb_path

def connect_to_duckdb(duckdb_path: Path)-> duckdb.DuckDBPyConnection:
    try:
        duckdb_connect = duckdb.connect(str(duckdb_path))
    except (duckdb.Error) as e:
        raise DuckDBDatabaseConnectionError() from e
    return duckdb_connect

def create_duckdb_table(duckdb_connect) -> None:
    try:
        cursor = duckdb_connect.cursor()
        schema_query = """
        CREATE TABLE IF NOT EXISTS document_analytics (
        document_identifier VARCHAR PRIMARY KEY,
        file_type VARCHAR,
        file_size BIGINT,
        category VARCHAR,
        subcategory VARCHAR,
        processed_at TIMESTAMPTZ,
        model_name_version VARCHAR,
        processing_duration DOUBLE,
        inference_duration_seconds DOUBLE,
        character_count BIGINT,
        word_count BIGINT,
        tokenizer_token_count BIGINT,
        tokens_prompt BIGINT,
        prompt_eval_count BIGINT,
        eval_count BIGINT,
        total_ollama_api_processing_duration DOUBLE,
        prompt_eval_duration BIGINT,
        prompt_eval_duration_seconds DOUBLE,
        max_ai_config_context_window_tokens BIGINT,
        max_burrowsift_processing_tokens_ceiling BIGINT);
        """
        cursor.execute(schema_query)
        duckdb_connect.commit()
    except (duckdb.Error) as e:
        raise DatabaseTableCreationError() from e



def request_document() -> str:
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    file_path: str = filedialog.askopenfilename(title="Select a document file", filetypes=[("Document files", "*.pdf *.docx *.txt")])


    root.destroy()  # Close the Tkinter window

    if file_path:
        print(f"Selected file: {file_path}")
        if not file_path.lower().endswith(('.pdf', '.docx', '.txt')):
            raise InvalidFileTypeError()
        elif not Path(file_path).is_file():
            raise InvalidFileError()
        return file_path
    else:
        sys.exit("No file selected. Exiting the program.")
    
def generate_unique_id() -> str:
    unique_id = str(uuid4())
    return unique_id

def start_processing_time():
    processing_time_start = time.perf_counter()
    return processing_time_start

MAX_DOCUMENT_TOKENS = 180000

def read_metadata(file_path: str) -> dict[str, Any]:
    if not Path(file_path).is_file(): 
        raise InvalidFileError()
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
        raise InvalidFileError()
    if not os.access(path=file_data_path, mode=os.R_OK):
        raise FileNotReadableError()
    file_extension: str = Path(file_data_path).suffix.lower()

    if file_extension == '.pdf':
        return read_pdf_content(file_data_path)

    if file_extension == '.docx':
        return read_docx_content(file_data_path)

    if file_extension == '.txt':
        return read_txt_content(file_data_path)

    raise InvalidFileTypeError()

def read_pdf_content(file_data_path: str) -> str:
    if not Path(file_data_path).is_file():
        raise InvalidFileError()
    if not os.access(path=file_data_path, mode=os.R_OK):
        raise FileNotReadableError()
    read_pdf: Any = PdfReader(stream=file_data_path)
    pdf_content: list[str] = []
    for page in read_pdf.pages:
        page_text: str = page.extract_text() or ""
        pdf_content.append(page_text)
    return "\n".join(pdf_content)

def read_docx_content(file_data_path: str) -> str:
    if not Path(file_data_path).is_file():
        raise InvalidFileError()
    if not os.access(path=file_data_path, mode=os.R_OK):
        raise FileNotReadableError()
    document: Any = Document(docx=file_data_path)
    docx_content: list[str] = []
    for paragraph in document.paragraphs:
        docx_content.append(paragraph.text)
    return "\n\n".join(docx_content)

def read_txt_content(file_data_path: str) -> str:
    if not Path(file_data_path).is_file():
        raise InvalidFileError()
    if not os.access(path=file_data_path, mode=os.R_OK):
        raise FileNotReadableError()
    with open(file=file_data_path, mode='r', encoding='utf-8') as text_file:
        text_content: str = text_file.read()
    return text_content

def gemma_token_count(text: str) -> int:
    token_ids: list[int] = tokenizer.encode( # pyright: ignore[reportUnknownMemberType]
        text,
        add_special_tokens=False,
    )
    return len(token_ids)

# Chunking to be added in in 0.3.0
def document_token_count_check(content: str) -> int:
    max_token_limit: int = MAX_DOCUMENT_TOKENS
    document_token_count: int = gemma_token_count(content)
    print(document_token_count)
    if document_token_count > max_token_limit:
        raise DocumentTooLargeError()
    return document_token_count

def document_character_count_check(content: str) -> int:
    character_count: int = len(content)
    return character_count

def word_count_check(content: str) -> int:
    word_count: int = len(content.split())
    return word_count

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
        raise DirectoryNotWritableError()   

    with open(file=output_path, mode='w', encoding='utf-8') as json_file:
        json.dump(obj=structured_dict, fp=json_file, indent=4)

def create_ollama_output_path(source_file_name: str, unique_id: str,)  -> tuple[Path, Path]:
    holding_dir: Path = Path(r"B:\Development\Projects\Learning\Python\BurrowSift\Holding")
    holding_dir.mkdir(parents=True, exist_ok=True)
    auto_file_name: Path = holding_dir / f"{source_file_name}__{unique_id}.json"
    path_tuple = (auto_file_name, holding_dir)
    return path_tuple


def turn_json_string_to_dict(json_string: str) -> dict[str, Any]:
    try:
        response_dict: dict[str, Any] = json.loads(json_string)
        return response_dict
    except json.JSONDecodeError as e:
        raise OllamaResponseDecodingError() from e

def write_ollama_response_to_json(temp_file: str, response_dict: dict[str, Any]) -> None:
    if not os.access(path=os.path.dirname(temp_file), mode=os.W_OK):
        raise DirectoryNotWritableError()

    with open(file=temp_file, mode='w', encoding='utf-8') as json_file:
        json.dump(obj=response_dict, fp=json_file, indent=4)


def send_to_ollama_api(structured_dict: dict[str, Any], source_file_name: str, unique_id: str,) -> tuple[dict[str, Any], int, int, int, int, float, int, float, str, int, int]:
    url = "http://localhost:11434/api/generate"

    structured_dict_json = json.dumps(structured_dict, indent=4)

    prompt = f"""
Analyze the supplied document and classify it for filing purposes.

Document:
{structured_dict_json}

Return ONLY a single JSON object containing exactly these keys:
'category', 'summary', 'subcategory', and 'tags'.

Classification rules:
- Classify the document according to its primary document type and intended purpose.
- Do not classify it only by topics, skills, industries, products, or subjects mentioned inside the document.
- Prefer the document's function over its subject matter.
- A resume that mentions education, programming, or research is still an employment resume.
- An invoice for computer equipment is still a finance invoice, not a technology document.
- A programming textbook is education or reference material, not an employment document.
- The category must be selected from the approved category values defined by the schema.
- The subcategory must be selected from the approved subcategory values defined by the schema.
- Do not invent new categories or subcategories.
- If the document does not clearly fit an approved classification, use the approved fallback classification.

Output requirements:
- 'category': the approved top-level filing category.
- 'subcategory': the approved filing subcategory that best matches the document's type and purpose.
- 'summary': a concise factual summary of the document's main purpose and key information.
- 'tags': a short list of meaningful topic labels that describe the document's content. Tags may describe subjects that are not part of the filing category.

Do not reproduce the supplied metadata or full document content.
Do not include explanations, commentary, markdown, or text outside the JSON object.
Ensure the response conforms exactly to the supplied JSON schema.
"""


    ai_model = "gemma4-12b-256k-test"
    model_num_ctx = 262144
    max_prompt_tokens = 220000

    tokens_prompt: int = gemma_token_count(text=prompt)
    if tokens_prompt > max_prompt_tokens:
        raise DocumentTooLargeError()

    payload_category_summary: dict[str, str | dict[str, str | dict[str, dict[str, str | list[str]] | dict[str, str] | dict[str, str | dict[str, str]]] | list[str] | bool | list[dict[str, dict[str, dict[str, str] | dict[str, list[str]] | dict[str, str | dict[str, str]]] | list[str]]]] | bool | dict[str, int]] = {
    "model": ai_model,
    "prompt": prompt,
    "format": {
    "type": "object",

    "properties": {
        "category": {
            "type": "string",
            "enum": [
                "Employment",
                "Finance",
                "Business",
                "Technology",
                "Education",
                "Legal",
                "Government",
                "Health",
                "Property",
                "Insurance",
                "Personal",
                "Reference",
                "Entertainment",
                "Other"
            ]
        },

        "summary": {
            "type": "string"
        },

        "subcategory": {
            "type": "string"
        },

        "tags": {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    },

    "required": [
        "category",
        "summary",
        "subcategory",
        "tags"
    ],

    "additionalProperties": False,

    "oneOf": [
        {
            "properties": {
                "category": {
                    "const": "Employment"
                },
                "subcategory": {
                    "enum": [
                        "Resumes",
                        "Cover Letters",
                        "Job Applications",
                        "Employment Contracts",
                        "Payslips",
                        "Performance & HR",
                        "Compliance",
                        "Job Advertisements",
                        "Payroll"
                    ]
                },
                "summary": {
                    "type": "string"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "category",
                "subcategory",
                "summary",
                "tags"
            ]
        },

        {
           "properties": {
               "category": {
                   "const": "Finance"
               },
               "subcategory": {
                   "enum":[
                       "Banking",
                       "Tax",
                       "Invoices",
                       "Receipts",
                       "Statements",
                       "Budgets",
                       "Investments"
                   ]
               },
               "summary": {
                   "type": "string"
               },
               "tags": {
                   "type": "array",
                   "items": {
                       "type": "string"
                   }
               }
           }, 
           "required": [
               "category",
               "subcategory",
               "summary",
               "tags"
           ]
        },

        {
            "properties": {
                "category": {
                    "const": "Business"
                },
                "subcategory": {
                    "enum":[
                        "Operations",
                        "Projects",
                        "Reports",
                        "Policies",
                        "Procedures",
                        "Proposals",
                        "Contracts",
                        "Research"
                    ]
                },
                "summary": {
                    "type": "string"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "category",
                "subcategory",
                "summary",
                "tags"
            ]
        },

        {
            "properties": {
                "category": {
                    "const": "Technology"
                },
                "subcategory": {
                    "enum":[
                        "Programming",
                        "Documentation",
                        "Systems",
                        "Infrastructure",
                        "Security",
                        "AI"
                    ]
                },
                "summary": {
                    "type": "string"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "category",
                "subcategory",
                "summary",
                "tags"
            ]
        },

        {
            "properties": {
                "category": {
                    "const": "Education"
                },
                "subcategory": {
                    "enum": [
                        "Reference Material",
                        "Courses",
                        "Assignments",
                        "Notes",
                        "Research",
                        "Qualifications",
                    ]
                },
                "summary": {
                    "type": "string"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "category",
                "subcategory",
                "summary",
                "tags"
            ]
        },

        {
            "properties": {
                "category": {
                    "const": "Legal"
                },
                "subcategory": {
                    "enum": [
                        "Agreements",
                        "Contracts",
                        "Correspondence",
                        "Court Documents",
                        "Legal Reference"
                    ]
                },
                "summary": {
                    "type": "string"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "category",
                "subcategory",
                "summary",
                "tags"
            ]
        },

        {
            "properties": {
                "category": {
                    "const": "Government"
                },
                "subcategory": {
                    "enum": [
                        "Tax",
                        "Benefits",
                        "Licences",
                        "Applications",
                        "Correspondence"
                    ]
                },
                "summary": {
                    "type": "string"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                } 
            },
            "required": [
                "category",
                "subcategory",
                "summary",
                "tags"
            ]
        },

        {
            "properties": {
                "category": {
                    "const": "Health"
                },
                "subcategory":{
                    "enum": [
                        "Medical Records",
                        "Test Results",
                        "Prescriptions",
                        "Appointments",
                        "Insurance"
                    ]
                },
                "summary": {
                    "type": "string"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "category",
                "subcategory",
                "summary",
                "tags"
            ]
        },

        {
            "properties": {
                "category": {
                    "const": "Property"
                },
                "subcategory": {
                    "enum": [
                        "Housing",
                        "Utilities",
                        "Maintenance",
                        "Leasing",
                        "Ownership"
                    ]
                },
                "summary": {
                    "type": "string"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "category",
                "subcategory",
                "summary",
                "tags"
            ]
        },

        {
            "properties": {
                "category": {
                    "const": "Insurance"
                },
                "subcategory": {
                    "enum": [
                        "Policies",
                        "Claims",
                        "Correspondence"
                    ]
                },
                "summary": {
                    "type": "string"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "category",
                "subcategory",
                "summary",
                "tags"
            ]
        },

        {
            "properties": {
                "category": {
                    "const": "Entertainment"
                },
                "subcategory": {
                    "enum": [
                        "Film",
                        "Television",
                        "Music",
                        "Video Games",
                        "Art",
                        "Theatre",
                        "Books & Literature",
                        "Festivals & Events",
                        "Comics & Manga",
                        "Podcasts",
                        "Photography",
                        "Collectibles",
                        "Reviews & Criticism",
                        "Guides & Reference"
                    ]
                },
                "summary": {
                    "type": "string"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "category",
                "subcategory",
                "summary",
                "tags"
            ]    
        },

        {
            "properties": {
                "category": {
                    "const": "Personal"
                },
                "subcategory": {
                    "enum": [
                        "Identification",
                        "Correspondence",
                        "Records",
                        "Miscellaneous"
                    ]
                },
                "summary": {
                    "type": "string"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "category",
                "subcategory",
                "summary",
                "tags"
            ]
        },

        {
            "properties": {
                "category": {
                    "const": "Reference"
                },
                "subcategory": {
                    "enum":[
                        "Manuals",
                        "Guides",
                        "Books",
                        "Articles",
                        "Research"
                    ]
                },
                "summary": {
                    "type": "string"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "category",
                "subcategory",
                "summary",
                "tags"
            ]
        },

        {
            "properties": {
                "category": {
                    "const": "Other"
                },
                "subcategory": {
                    "enum": [
                        "Uncategorized"
                    ]
                },
                "summary": {
                    "type": "string"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "category",
                "subcategory",
                "summary",
                "tags"
            ]
        }
    ]
},
    "stream": False,
    "think": False,
    "options": {
        "num_ctx": model_num_ctx,
        },
    }

    try:
        response_category_summary = requests.post(url, json=payload_category_summary, timeout=(10, 300))
    except RequestException as e:
        raise OllamaAPIError() from e

    if response_category_summary.status_code == 200:
        ollama_response_json: dict[str, Any] = response_category_summary.json() #Could Fail if the response is not valid JSON, but we are assuming it is valid JSON for now.

        prompt_tokens: int = ollama_response_json.get("prompt_eval_count", 0)
        completion_tokens: int = ollama_response_json.get("eval_count", 0)
        inference_duration: int = ollama_response_json.get("eval_duration", 0)
        inference_duration_seconds: float = inference_duration / 1000000000
        prompt_eval_duration: int = ollama_response_json.get("prompt_eval_duration", 0)
        prompt_eval_duration_seconds: float = prompt_eval_duration / 1000000000


        json_string: str = ollama_response_json["response"]


        response_data: dict[str, Any] = turn_json_string_to_dict(json_string=json_string)

        print("GEMMA RESPONSE:")
        print(json.dumps(response_data, indent=4))

        ollama_response_validation(response_dict=response_data)
        print(response_data)
        print(f"Tokenizercount: {tokens_prompt}")
        print(f"Prompt tokens used: {prompt_tokens}")
        print(f"Completion tokens used: {completion_tokens}")
        return response_data, prompt_tokens, completion_tokens, tokens_prompt, inference_duration, inference_duration_seconds, prompt_eval_duration, prompt_eval_duration_seconds, ai_model, model_num_ctx, max_prompt_tokens,
    else:
        raise OllamaAPIError()

def ollama_response_validation(response_dict: dict[str, Any]) -> None:
    required_keys = {"category":str, "summary":str, "subcategory":str, "tags": list}
    if not set(required_keys).issubset(response_dict.keys()):
        raise OllamaResponseFormatError()
    for key, expected_type in required_keys.items():
        if not isinstance(response_dict[key], expected_type):
            raise OllamaResponseFormatError()
    for tags in response_dict["tags"]:
        if not isinstance(tags, str):
            raise OllamaResponseFormatError()

def build_processing_stats(character_count:int, word_count:int, tokenizer_token_count:int, prompt_tokens:int, completion_tokens:int, tokens_prompt: int, inference_duration: int, inference_duration_seconds: float, prompt_eval_duration: int, prompt_eval_duration_seconds: float) -> dict[str, int|float]:
    processing_stats: dict[str, int|float] = {"character_count": character_count, "word_count": word_count, "tokenizer_token_count": tokenizer_token_count, "tokens_prompt": tokens_prompt, "prompt_eval_count": prompt_tokens, "eval_count": completion_tokens, "inference_duration": inference_duration, "inference_duration_seconds": inference_duration_seconds, "prompt_eval_duration": prompt_eval_duration, "prompt_eval_duration_seconds": prompt_eval_duration_seconds}
    return processing_stats

def build_final_json_record(metadata: dict[str, Any], content: str, ollama_response: dict[str, Any], unique_id: str, source_file_name: str, processing_stats:dict[str, int| float]) -> dict[str, Any]:
    final_record: dict[str, Any] = {
        "metadata": metadata,
        "document_identifier": unique_id,
        "processing_stats": processing_stats,
        "source_file_name": source_file_name,
        "ollama_response": ollama_response,   
    }
    return final_record

def write_final_record_to_json(final_record: dict[str, Any], auto_file_name: Path) -> Path:
    if not os.access(path=os.path.dirname(p=auto_file_name), mode=os.W_OK):
        raise DirectoryNotWritableError()   

    with open(file=auto_file_name, mode='w', encoding='utf-8') as json_file:
        json.dump(obj=final_record, fp=json_file, indent=4)

    return auto_file_name

def pair_identity(unique_id: str, moved_original_file: Path, ollama_output_path: Path) -> dict[str, tuple[Path, Path]]: 
    staged_pair: tuple[Path, Path] = (moved_original_file, ollama_output_path)
    id_staged_pair: dict[str, tuple[Path, Path]] = {unique_id: staged_pair}
    return id_staged_pair

def pair_contents_validation(unique_id:str ,id_staged_pair:dict[str,tuple[Path, Path]]) -> None:
    if unique_id not in id_staged_pair:
        raise StagedPairNotFoundError()
    get_staged_pair: tuple[Path, Path] = id_staged_pair[unique_id]
    moved_original_file, ollama_output_path = get_staged_pair
    if not moved_original_file.is_file():
        raise OriginalFileNotFoundError()
    if not ollama_output_path.is_file():
        raise JSONFileNotFoundError()

def routing_destination(auto_file_name: Path) -> tuple[str, str]:
    with open(file=auto_file_name, mode='r', encoding='utf-8') as file:
        content: dict[str, Any] = json.load(file)
        sort_category: str = content["ollama_response"]["category"]
        sort_subcategory: str = content["ollama_response"]["subcategory"]
        sort_tuple: tuple[str, str] = (sort_category, sort_subcategory)
        return sort_tuple

def build_destination_path(sort_tuple: tuple[str, str]) -> Path:
    sort_category, sort_subcategory = sort_tuple
    burrowsift_sort_dir = Path(r"B:\Burrowsift\Sorted_files")/sort_category/sort_subcategory #Will need to let users create the initial parent directory upon setup so no hardcoding
    burrowsift_sort_dir.mkdir(parents=True, exist_ok=True)
    return burrowsift_sort_dir   

def move_paired_files(unique_id: str, id_staged_pair: dict[str, tuple[Path, Path]], burrowsift_sort_dir: Path) -> tuple[Path, Path]:
    moved_original_file, ollama_output_path = id_staged_pair[unique_id]
    try:
        sorted_original_file_path = Path(shutil.move(src=moved_original_file, dst=burrowsift_sort_dir))
    except (OSError, shutil.Error) as error:
        raise OriginalFileSortError() from error
    if not sorted_original_file_path.is_file():
        raise OriginalFileSortError()
    try:
        sorted_ollama_file_path = Path(shutil.move(src=ollama_output_path, dst=burrowsift_sort_dir))
    except (OSError, shutil.Error) as error:
        try:
            move_back_original_file = Path(shutil.move(src=sorted_original_file_path, dst=moved_original_file))
        except (OSError, shutil.Error) as rollback_error:
            raise FileSortRollbackError() from rollback_error
        if not move_back_original_file.is_file():
            raise FileSortRollbackError()
        raise JSONFileSortError() from error
    if not sorted_ollama_file_path.is_file():
        try:
            move_back_original_file = Path(shutil.move(src=sorted_original_file_path, dst=moved_original_file))
        except (OSError, shutil.Error) as rollback_error:
            raise FileSortRollbackError() from rollback_error
        if not move_back_original_file.is_file():
            raise FileSortRollbackError()
        raise JSONFileSortError()
    return sorted_original_file_path, sorted_ollama_file_path

def end_processing_time():
    processing_time_end = time.perf_counter()
    return processing_time_end

def calc_total_processing_time(procesing_time_start, processing_time_end):
    processing_duration = processing_time_end - procesing_time_start
    return processing_duration
    
def add_to_final_record(final_record: dict[str, Any], sorted_original_file_path, sorted_ollama_file_path, total_ollama_processing_duration, total_doc_processing_duration, ai_model, model_num_ctx, max_prompt_tokens):
    final_record["current_file_path"] = str(sorted_original_file_path)
    final_record["json_file_path"] = str(sorted_ollama_file_path)
    final_record["total_ollama_processing_duration"] = total_ollama_processing_duration
    final_record["total_doc_processing_duration"] = total_doc_processing_duration
    final_record["ai_model"] = ai_model
    final_record["model_max_tokens"] = model_num_ctx
    final_record["max_processing_tokens"] = max_prompt_tokens
    return final_record

def extract_finalrecord_values_for_sqlite(final_record: dict[str, Any])-> dict[str, Any]:
    local_time = datetime.now().astimezone().isoformat()
    sql_dict = {"document_identifier": final_record["document_identifier"],
        "source_file_name": final_record["metadata"]["file_name"],
        "original_file_path": final_record["metadata"]["absolute_path"],
        "current_file_path": final_record["current_file_path"],
        "json_file_path": final_record["json_file_path"],
        "file_type": final_record["metadata"]["file_type"],
        "file_size": final_record["metadata"]["file_size"],
        "category": final_record["ollama_response"]["category"],
        "subcategory": final_record["ollama_response"]["subcategory"],
        "summary_text": final_record["ollama_response"]["summary"],
        "processed_at": local_time,
        "processing_duration": final_record["total_doc_processing_duration"],
        "total_ollama_api_processing_duration": final_record["total_ollama_processing_duration"],
        "inference_duration_seconds": final_record["processing_stats"]["inference_duration_seconds"],
        "prompt_eval_duration": final_record["processing_stats"]["prompt_eval_duration"],
        "prompt_eval_duration_seconds": final_record["processing_stats"]["prompt_eval_duration_seconds"],
        "model_name_version": final_record["ai_model"],
        "max_ai_config_context_window_tokens": final_record["model_max_tokens"],
        "max_burrowsift_processing_tokens_ceiling": final_record["max_processing_tokens"],
        "word_count": final_record["processing_stats"]["word_count"],
        "character_count": final_record["processing_stats"]["character_count"],
        "tokenizer_token_count": final_record["processing_stats"]["tokenizer_token_count"],
        "tokens_prompt": final_record["processing_stats"]["tokens_prompt"],
        "prompt_eval_count": final_record["processing_stats"]["prompt_eval_count"],
        "eval_count": final_record["processing_stats"]["eval_count"],
        }
    return sql_dict

def insert_dict_into_sql(sql_dict: dict[str, Any], db_connect: sqlite3.Connection)-> None:
    try:    
        cursor = db_connect.cursor()
        columns = ", ".join(sql_dict.keys())
        placeholders = ", ".join([f":{key}" for key in sql_dict.keys()])
        query = f"INSERT INTO documents ({columns}) VALUES ({placeholders})"
        cursor.execute(query, sql_dict)
        db_connect.commit()
    except (sqlite3.Error) as error:
        db_connect.rollback()
        raise DatabaseInsertionError() from error

def retrieve_doc_analytics_from_sqlite(unique_id, db_connect):
    cursor = db_connect.cursor()

    query = """SELECT
    "document_identifier",
    "file_type",
    "file_size",
    "category",
    "subcategory",
    "processed_at",
    "model_name_version",
    "processing_duration",
    "inference_duration_seconds",
    "character_count",
    "word_count",
    "tokenizer_token_count",
    "tokens_prompt",
    "prompt_eval_count",
    "eval_count",
    "total_ollama_api_processing_duration",
    "prompt_eval_duration",
    "prompt_eval_duration_seconds",
    "max_ai_config_context_window_tokens",
    "max_burrowsift_processing_tokens_ceiling"
    from documents
    WHERE "document_identifier" = ?
    """
    cursor.execute(query, (unique_id,))
    row = cursor.fetchone()
    if row is None:
        raise NoUUIDMatch()
    column_names = [description[0] for description in cursor.description]
    analytics_dict = dict(zip(column_names, row))
    return analytics_dict



def error_helper(error: Exception) -> None:
    print(f"Error: {error}")
    
def main() -> None:
    while True:
        try:
            automatic_ollama_start()
        except (OllamaAPIError) as error:
            error_helper(error)
            continue  
        try:
            db_path: Path = create_or_open_database()
        except (DatabaseCreationError) as error:
            error_helper(error)
            break
        try:
            db_connection: sqlite3.Connection = connect_sqlite(data_base_path=db_path)
        except (DatabaseConnectionError) as error:
            error_helper(error)
            break
        try:
            create_db_table(db_connect=db_connection)
        except (DatabaseTableCreationError) as error:
            error_helper(error)
            break
        try:
            alter_update_sqlite_table(db_connection)
        except (DatabaseTableAlterError) as error:
            error_helper(error)
            break
        try:
            duckdb_path = create_or_open_duckdb_path()
        except (DatabaseCreationError) as error:
            error_helper(error)
            break
        try:
            duckdb_connection = connect_to_duckdb(duckdb_path)
        except (DuckDBDatabaseConnectionError) as error:
            error_helper(error)
            break
        try:
            create_duckdb_table(duckdb_connection)
        except (DatabaseTableCreationError) as error:
            error_helper(error)
            break
        try:
            file_path: str = request_document()
            start_time = start_processing_time()
        except (InvalidFileError, InvalidFileTypeError) as error:
            error_helper(error)
            continue  # Prompt the user to select a file again
        try:
            metadata: dict[str, Any] = read_metadata(file_path)
            content: str = read_content(file_data_path=file_path)
            character_count: int = document_character_count_check(content)
            word_count: int = word_count_check(content)
            tokenizer_token_count: int = document_token_count_check(content)
        except (InvalidFileError, InvalidFileTypeError, FileNotReadableError, DocumentTooLargeError) as error:
            error_helper(error)
            continue  # Prompt the user to select a file again
        print(f"character count: {character_count}")
        print(f"Word count: {word_count}")
        print(f"tokenizer token count: {tokenizer_token_count}")
        structured_content: dict[str, Any] = build_structured_content(metadata, content)
        
        source_file_name: str = Path(file_path).stem
        unique_id: str = generate_unique_id()
        while True:
            try:
                ollama_api_response_time_start = time.perf_counter()
                ollama_response, prompt_tokens, completion_tokens, tokens_prompt, inference_duration, inference_duration_seconds, prompt_eval_duration, prompt_eval_duration_seconds, ai_model, model_num_ctx, max_prompt_tokens = send_to_ollama_api(
                    structured_dict=structured_content,
                    source_file_name=source_file_name,
                    unique_id=unique_id,
                )
                processing_stats: dict[str, Any] = build_processing_stats(
                            character_count,
                            word_count,
                            tokenizer_token_count,
                            prompt_tokens,
                            completion_tokens,
                            tokens_prompt,
                            inference_duration,
                            inference_duration_seconds,
                            prompt_eval_duration,
                            prompt_eval_duration_seconds,
                        )
                ollama_api_response_time_end = time.perf_counter()
                total_ollama_api_processing_duration = ollama_api_response_time_end - ollama_api_response_time_start
            except (OllamaAPIError, OllamaResponseError, DirectoryNotWritableError,) as error:
                error_helper(error)
                continue  # Retry Ollama processing
            break  # Exit the inner loop if no exception occurs
        final_record: dict[str, Any] = build_final_json_record(metadata, content, ollama_response, unique_id, source_file_name, processing_stats)
        while True:
            try:
                auto_named_file,  holding_dir, = create_ollama_output_path(source_file_name, unique_id)
                
                ollama_output_holding_path: Path = write_final_record_to_json(final_record, auto_file_name=auto_named_file)
            except (DirectoryNotWritableError) as error:
                error_helper(error)
                continue
            try:
                moved_original_file: Path = Path(shutil.move(src=file_path, dst=holding_dir))
            except (OSError, shutil.Error) as error:
                error_helper(error)
                break
            try:    
                id_staged_pair: dict[str, tuple[Path, Path]] = pair_identity(unique_id, moved_original_file, ollama_output_path=ollama_output_holding_path)
                pair_contents_validation(unique_id, id_staged_pair)
            except (StagedPairNotFoundError, OriginalFileNotFoundError, JSONFileNotFoundError) as error:
                error_helper(error)
                break
            try:
                sort_tuple: tuple[str, str] = routing_destination(auto_file_name=ollama_output_holding_path)
                built_path: Path = build_destination_path(sort_tuple)
            except (OSError, json.JSONDecodeError, KeyError) as error:
                error_helper(error)
                break
            try:
                sorted_original_file_path, sorted_ollama_file_path = move_paired_files(unique_id, id_staged_pair, burrowsift_sort_dir=built_path)
                end_time = end_processing_time()
                processing_duration = calc_total_processing_time(start_time, end_time)
            except (OriginalFileSortError, JSONFileSortError, FileSortRollbackError) as error:
                error_helper(error)
                break
            try:
                final_record_sql = add_to_final_record(final_record, sorted_original_file_path, sorted_ollama_file_path, total_ollama_api_processing_duration, processing_duration, ai_model, model_num_ctx, max_prompt_tokens)
                extract_record = extract_finalrecord_values_for_sqlite(final_record_sql)
                insert_dict = insert_dict_into_sql(extract_record, db_connection)
            except (DatabaseInsertionError, DatabaseTableAlterError) as error:
                error_helper(error)
                break
            print(f"Metadata: {metadata}")
            print(f"Content preview: {content[:100] if content else 'No content'}")
            break
        break  # Exit the loop if no exception occurs

if __name__ == "__main__":
    main()


