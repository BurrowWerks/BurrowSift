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

class InvalidFileTypeError(ValueError):
    statement = ("Invalid file type. Please select a document file of types PDF, DOCX, or TXT.")
    def __init__(self):
            super().__init__(self.statement)
class DocumentTooLargeError(ValueError):
    statement = ("The document exceeds the maximum supported token limit. Please select a smaller document.")
    def __init__(self):
            super().__init__(self.statement)
class InvalidFileError(FileNotFoundError):
    statement = ("The selected file is not valid. Please select a document file of types PDF, DOCX, or TXT.")
    def __init__(self):
            super().__init__(self.statement)
class FileNotReadableError(PermissionError):
    statement = ("The selected file is not readable. Please select a different file.")
    def __init__(self):
            super().__init__(self.statement)


class DirectoryNotWritableError(PermissionError):
    statement = ("The selected directory is not writable. Please select a different directory.")
    def __init__(self):
            super().__init__(self.statement)

class DirectoryNotReadableError(PermissionError):
    statement = ("The selected directory is not readable. Please select a different directory.")
    def __init__(self):
            super().__init__(self.statement)

class OllamaAPIError(RequestException):
    statement = ("Error occurred while communicating with the Ollama API.")
    def __init__(self):
            super().__init__(self.statement)

class OllamaResponseError(ValueError):
    statement = ("Error occurred while processing the Ollama API response.")
    
    def __init__(self):
        super().__init__(self.statement)

class OllamaResponseDecodingError(OllamaResponseError):
    statement = ("Error occurred while decoding the Ollama API response.")

class OllamaResponseFormatError(OllamaResponseError):
    statement = ("Error occurred due to an unexpected format in the Ollama API response.")
    
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
    return str(uuid4())

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

def create_ollama_output_path(source_file_name: str, unique_id: str,) -> str:
    holding_dir: Path = Path(r"B:\Development\Projects\Learning\Python\BurrowSift\Holding")
    holding_dir.mkdir(parents=True, exist_ok=True)
    auto_file_name: Path = holding_dir / f"{source_file_name}__{unique_id}.json"
    return str(auto_file_name)

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


def send_to_ollama_api(structured_dict: dict[str, Any], source_file_name: str, unique_id: str,) -> tuple[dict[str, Any], int, int, int]:
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


    OLLAMA_MODEL = "gemma4-12b-256k-test"
    OLLAMA_NUM_CTX = 262144
    MAX_OLLAMA_PROMPT_TOKENS = 220000

    tokens_prompt: int = gemma_token_count(prompt)
    if tokens_prompt > MAX_OLLAMA_PROMPT_TOKENS:
        raise DocumentTooLargeError()

    payload_category_summary = {
    "model": OLLAMA_MODEL,
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
        "num_ctx": OLLAMA_NUM_CTX,
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

        json_string: str = ollama_response_json["response"]


        response_data: dict[str, Any] = turn_json_string_to_dict(json_string=json_string)

        print("GEMMA RESPONSE:")
        print(json.dumps(response_data, indent=4))

        ollama_response_validation(response_dict=response_data)
        print(response_data)
        print(f"Tokenizercount: {tokens_prompt}")
        print(f"Prompt tokens used: {prompt_tokens}")
        print(f"Completion tokens used: {completion_tokens}")
        return response_data, prompt_tokens, completion_tokens, tokens_prompt
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

def build_processing_stats(character_count:int, word_count:int, tokenizer_token_count:int, prompt_tokens:int, completion_tokens:int, tokens_prompt: int) -> dict[str, int]:
    processing_stats: dict[str, int] ={"character_count": character_count, "word_count": word_count, "tokenizer_token_count": tokenizer_token_count, "tokens_prompt": tokens_prompt, "prompt_eval_count": prompt_tokens, "eval_count": completion_tokens}
    return processing_stats

def build_final_json_record(metadata: dict[str, Any], content: str, ollama_response: dict[str, Any], unique_id: str, source_file_name: str, processing_stats:dict[str, int]) -> dict[str, Any]:
    final_record: dict[str, Any] = {
        "metadata": metadata,
        "document_identifier": unique_id,
        "processing_stats": processing_stats,
        "source_file_name": source_file_name,
        "ollama_response": ollama_response,
        
    }
    return final_record

def write_final_record_to_json(final_record: dict[str, Any], auto_file_name:str) -> None:
    if not auto_file_name:
        return  # User canceled the save dialog
    if not os.access(path=os.path.dirname(auto_file_name), mode=os.W_OK):
        raise DirectoryNotWritableError()   

    with open(file=auto_file_name, mode='w', encoding='utf-8') as json_file:
        json.dump(obj=final_record, fp=json_file, indent=4)

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
            file_path: str = request_document()
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
                ollama_response, prompt_tokens, completion_tokens, tokens_prompt = send_to_ollama_api(
                    structured_dict=structured_content,
                    source_file_name=source_file_name,
                    unique_id=unique_id,
                )
                processing_stats: dict[str, int] = build_processing_stats(
                            character_count,
                            word_count,
                            tokenizer_token_count,
                            prompt_tokens,
                            completion_tokens,
                            tokens_prompt,
                        )
            except (OllamaAPIError, OllamaResponseError, DirectoryNotWritableError,) as error:
                error_helper(error)
                continue  # Retry Ollama processing
            break  # Exit the inner loop if no exception occurs
        final_record: dict[str, Any] = build_final_json_record(metadata, content, ollama_response, unique_id, source_file_name, processing_stats)
        while True:
            try:
                auto_named_file: str = create_ollama_output_path(source_file_name, unique_id)
                write_final_record_to_json(final_record, auto_file_name=auto_named_file)
            except (DirectoryNotWritableError) as error:
                error_helper(error)
                continue
            print(f"Metadata: {metadata}")
            print(f"Content preview: {content[:100] if content else 'No content'}")
            break
        break  # Exit the loop if no exception occurs

if __name__ == "__main__":
    main()


