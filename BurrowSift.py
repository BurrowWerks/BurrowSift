import constants
from typing import Any
import sys
from tkinter import filedialog
import tkinter as tk
from pathlib import Path
from documents.readers import read_content
import json
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
from AI_payload import build_AI_config_parameters, build_AI_payload_category_summary, build_AI_prompt_payload
import exceptions
from documents.metadata import read_metadata
from documents.readers import read_content
from documents.tokens import document_token_count_check, gemma_token_count
from processing.statistics import document_character_count_check, word_count_check, start_processing_time, end_processing_time, calc_total_processing_time
from processing.records import build_final_json_record, add_to_final_record, build_structured_content
from storage.json_store import write_final_record_to_json



def automatic_ollama_start() -> subprocess.Popen[bytes] | None:
    try:
        response: requests.Response = requests.get(url="http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("Ollama API is already running.")
            return None
    except RequestException:
        pass  # Ollama API is not running, proceed to start it

    try:
        ollama_env = os.environ.copy()
        ollama_env["OLLAMA_FLASH_ATTENTION"] = "1"
        ollama_env["OLLAMA_KV_CACHE_TYPE"] = "q8_0"

        ollama_process = subprocess.Popen(args=["ollama", "serve"], env=ollama_env,)
        
        for _ in range(10):  # Poll up to 10 times
            try:
                polling_response = requests.get("http://localhost:11434/api/tags", timeout=1)
                if polling_response.status_code == 200:
                    print("Ollama API started successfully.")
                    return ollama_process  # Ollama API is now running
            except RequestException:
                pass  # Continue polling
            time.sleep(1)  # Wait for 1 second before the next poll
            if ollama_process.poll() is not None:
                print("Ollama process terminated unexpectedly.")
                raise exceptions.OllamaAPIError()
        ollama_process.terminate()  # Terminate the process if it didn't start successfully
        try:
            ollama_process.wait(timeout=5)  # Wait for the process to terminate
        except subprocess.TimeoutExpired:
            ollama_process.kill()  # Force kill if it didn't terminate
            ollama_process.wait()  # Wait for the process to be killed
        raise exceptions.OllamaAPIError()
    except exceptions.OllamaAPIError:
        raise 
    except Exception as e:
        raise exceptions.OllamaAPIError() from e

def create_or_open_database() -> Path:
    try:
        data_base_dir: Path= Path(r"B:\BurrowSift\Database")
        data_base_dir.mkdir(parents=True, exist_ok=True)
        data_base_path: Path = data_base_dir/"burrowsift.db"
    except (OSError) as e:
        raise exceptions.DatabaseCreationError() from e
    return data_base_path

def connect_sqlite(data_base_path: Path) -> sqlite3.Connection:
    try:
        db_connect: sqlite3.Connection = sqlite3.connect(data_base_path)
    except (sqlite3.Error) as e:
        raise exceptions.DatabaseConnectionError() from e
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
        raise exceptions.DatabaseTableCreationError() from e

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
        raise exceptions.DatabaseTableAlterError() from e


def create_or_open_duckdb_path()-> Path:
    try:
        duckdb_dirs: Path = Path(r"B:\BurrowSift\Database")
        duckdb_dirs.mkdir(parents=True, exist_ok=True)
        duckdb_path: Path = duckdb_dirs/"burrowsift.analytics.duckdb"
    except (OSError) as e:
        raise exceptions.DatabaseCreationError() from e
    return duckdb_path

def connect_to_duckdb(duckdb_path: Path)-> duckdb.DuckDBPyConnection:
    try:
        duckdb_connect = duckdb.connect(str(duckdb_path))
    except (duckdb.Error) as e:
        raise exceptions.DuckDBDatabaseConnectionError() from e
    return duckdb_connect

def create_duckdb_table(duckdb_connect: duckdb.DuckDBPyConnection) -> None:
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
        raise exceptions.DatabaseTableCreationError() from e

def close_sqlite_connection(db_connect: sqlite3.Connection) -> None:
    try:
        db_connect.close()
    except (sqlite3.Error) as e:
        raise exceptions.DatabaseCloseError() from e

def close_duckdb_connection(duckdb_connect: duckdb.DuckDBPyConnection) -> None:
    try:
        duckdb_connect.close()
    except (duckdb.Error) as e:
        raise exceptions.DuckDBDatabaseCloseError() from e


def request_document() -> str:
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    file_path: str = filedialog.askopenfilename(title="Select a document file", filetypes=[("Document files", "*.pdf *.docx *.txt")])


    root.destroy()  # Close the Tkinter window

    if file_path:
        print(f"Selected file: {file_path}")
        if not file_path.lower().endswith(constants.SUPPORTED_FILE_TYPES):
            raise exceptions.InvalidFileTypeError()
        elif not Path(file_path).is_file():
            raise exceptions.InvalidFileError()
        return file_path
    else:
        sys.exit("No file selected. Exiting the program.")
    
def generate_unique_id() -> str:
    unique_id = str(uuid4())
    return unique_id

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
        raise exceptions.OllamaResponseDecodingError() from e

def send_to_ollama_api(structured_dict: dict[str, Any], source_file_name: str, unique_id: str,) -> tuple[dict[str, Any], int, int, int, int, float, int, float, str, int, int]:
    url = "http://localhost:11434/api/generate"

    structured_dict_json = json.dumps(structured_dict, indent=4)

    prompt: str = build_AI_prompt_payload(structured_dict_json=structured_dict_json)

    ai_config = build_AI_config_parameters()

    if "ai_model" not in ai_config or "model_num_ctx" not in ai_config or "max_prompt_tokens" not in ai_config:
        raise KeyError("Missing required AI configuration keys.")

    ai_model = ai_config["ai_model"]
    model_num_ctx = ai_config["model_num_ctx"]
    max_prompt_tokens = ai_config["max_prompt_tokens"]

    if not isinstance(ai_model, str) or not isinstance(model_num_ctx, int) or not isinstance(max_prompt_tokens, int):
        raise exceptions.InvalidAIConfigError()
       
    if model_num_ctx <= 0 or max_prompt_tokens <= 0:
        raise exceptions.InvalidAIConfigError()
    
    if (model_num_ctx-max_prompt_tokens < 16384):
        raise exceptions.InvalidAIConfigError()
    
    tokens_prompt: int = gemma_token_count(text=prompt)
    if tokens_prompt > max_prompt_tokens:
        raise exceptions.DocumentTooLargeError()

    payload_category_summary: dict[str, Any] = build_AI_payload_category_summary(
        ai_model=ai_model,
        prompt=prompt,
        model_num_ctx=model_num_ctx,
    )

    try:
        response_category_summary = requests.post(url, json=payload_category_summary, timeout=(10, 300))
    except RequestException as e:
        raise exceptions.OllamaAPIError() from e

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
        raise exceptions.OllamaAPIError()

def ollama_response_validation(response_dict: dict[str, Any]) -> None:
    required_keys = {"category":str, "summary":str, "subcategory":str, "tags": list}
    if not set(required_keys).issubset(response_dict.keys()):
        raise exceptions.OllamaResponseFormatError()
    for key, expected_type in required_keys.items():
        if not isinstance(response_dict[key], expected_type):
            raise exceptions.OllamaResponseFormatError()
    for tags in response_dict["tags"]:
        if not isinstance(tags, str):
            raise exceptions.OllamaResponseFormatError()

def build_processing_stats(character_count:int, word_count:int, tokenizer_token_count:int, prompt_tokens:int, completion_tokens:int, tokens_prompt: int, inference_duration: int, inference_duration_seconds: float, prompt_eval_duration: int, prompt_eval_duration_seconds: float) -> dict[str, int|float]:
    processing_stats: dict[str, int|float] = {"character_count": character_count, "word_count": word_count, "tokenizer_token_count": tokenizer_token_count, "tokens_prompt": tokens_prompt, "prompt_eval_count": prompt_tokens, "eval_count": completion_tokens, "inference_duration": inference_duration, "inference_duration_seconds": inference_duration_seconds, "prompt_eval_duration": prompt_eval_duration, "prompt_eval_duration_seconds": prompt_eval_duration_seconds}
    return processing_stats

def pair_identity(unique_id: str, moved_original_file: Path, ollama_output_path: Path) -> dict[str, tuple[Path, Path]]: 
    staged_pair: tuple[Path, Path] = (moved_original_file, ollama_output_path)
    id_staged_pair: dict[str, tuple[Path, Path]] = {unique_id: staged_pair}
    return id_staged_pair

def pair_contents_validation(unique_id:str ,id_staged_pair:dict[str,tuple[Path, Path]]) -> None:
    if unique_id not in id_staged_pair:
        raise exceptions.StagedPairNotFoundError()
    get_staged_pair: tuple[Path, Path] = id_staged_pair[unique_id]
    moved_original_file, ollama_output_path = get_staged_pair
    if not moved_original_file.is_file():
        raise exceptions.OriginalFileNotFoundError()
    if not ollama_output_path.is_file():
        raise exceptions.JSONFileNotFoundError()

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
        raise exceptions.OriginalFileSortError() from error
    if not sorted_original_file_path.is_file():
        raise exceptions.OriginalFileSortError()
    try:
        sorted_ollama_file_path = Path(shutil.move(src=ollama_output_path, dst=burrowsift_sort_dir))
    except (OSError, shutil.Error) as error:
        try:
            move_back_original_file = Path(shutil.move(src=sorted_original_file_path, dst=moved_original_file))
        except (OSError, shutil.Error) as rollback_error:
            raise exceptions.FileSortRollbackError() from rollback_error
        if not move_back_original_file.is_file():
            raise exceptions.FileSortRollbackError()
        raise exceptions.JSONFileSortError() from error
    if not sorted_ollama_file_path.is_file():
        try:
            move_back_original_file = Path(shutil.move(src=sorted_original_file_path, dst=moved_original_file))
        except (OSError, shutil.Error) as rollback_error:
            raise exceptions.FileSortRollbackError() from rollback_error
        if not move_back_original_file.is_file():
            raise exceptions.FileSortRollbackError()
        raise exceptions.JSONFileSortError()
    return sorted_original_file_path, sorted_ollama_file_path
    
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
        raise exceptions.DatabaseInsertionError() from error

def retrieve_doc_analytics_from_sqlite(unique_id: str, db_connect: sqlite3.Connection):
    try:
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
            raise exceptions.NoUUIDMatch()
        column_names = [description[0] for description in cursor.description]
        analytics_dict = dict(zip(column_names, row))
    except (sqlite3.Error) as error:
        raise exceptions.DatabaseRetrievalError() from error
    return analytics_dict

def retrieve_all_document_identifiers_from_sqlite(db_connect: sqlite3.Connection) -> set[str]:
    try:
        cursor: sqlite3.Cursor = db_connect.cursor()
        query = """SELECT "document_identifier" FROM documents"""
        cursor.execute(query)
        rows: list[Any] = cursor.fetchall()
        document_identifiers_sqlite = {row[0] for row in rows}
        return document_identifiers_sqlite
    except (sqlite3.Error) as error:
        raise exceptions.DatabaseRetrievalError() from error

def insert_doc_analytics_into_duckdb(analytics_dict: dict[str, Any], duckdb_connection: duckdb.DuckDBPyConnection) -> None:
    try:
        cursor = duckdb_connection.cursor()
        columns = ", ".join(analytics_dict.keys())
        placeholders = ", ".join(["?"] * len(analytics_dict))
        query = f"INSERT INTO document_analytics ({columns}) VALUES ({placeholders})"
        cursor.execute(query, list(analytics_dict.values()))
        duckdb_connection.commit()
    except (duckdb.Error) as error:
        duckdb_connection.rollback()
        raise exceptions.DuckDBInsertionError() from error

def retrieve_all_document_identifiers_from_duckdb(duckdb_connection: duckdb.DuckDBPyConnection) -> set[str]:
    try:
        cursor = duckdb_connection.cursor()
        query = """SELECT "document_identifier" FROM document_analytics"""
        cursor.execute(query)
        rows = cursor.fetchall()
        document_identifiers_duckdb = {row[0] for row in rows}
    except (duckdb.Error) as error:
        raise exceptions.DuckDBRetrievalError() from error
    return document_identifiers_duckdb

def compare_sqlite_and_duckdb_identifiers(sqlite_identifiers: set[str], duckdb_identifiers: set[str]) -> set[str]:
    missing_in_duckdb = sqlite_identifiers - duckdb_identifiers
    return missing_in_duckdb

def insert_missing_identifiers_into_duckdb(missing_identifiers: set[str], db_connection: sqlite3.Connection, duckdb_connection: duckdb.DuckDBPyConnection) -> None:
    for unique_id in missing_identifiers:
        missing_analytics_dict = retrieve_doc_analytics_from_sqlite(unique_id, db_connection)
        insert_doc_analytics_into_duckdb(missing_analytics_dict, duckdb_connection)

def error_helper(error: Exception) -> None:
    print(f"Error: {error}")
    
def main() -> None:
    while True:
        db_connection: sqlite3.Connection | None = None
        duckdb_connection: duckdb.DuckDBPyConnection | None = None
        ollama_process: subprocess.Popen[bytes] | None = None
        try:
            try:
                ollama_process = automatic_ollama_start()
            except (exceptions.OllamaAPIError) as error:
                error_helper(error)
                continue  
            try:
                db_path: Path = create_or_open_database()
            except (exceptions.DatabaseCreationError) as error:
                error_helper(error)
                break
            try:
                db_connection = connect_sqlite(data_base_path=db_path)
            except (exceptions.DatabaseConnectionError) as error:
                error_helper(error)
                break 
            try:
                create_db_table(db_connect=db_connection)
            except (exceptions.DatabaseTableCreationError) as error:
                error_helper(error)
                break
            try:
                alter_update_sqlite_table(db_connection)
            except (exceptions.DatabaseTableAlterError) as error:
                error_helper(error)
                break 
            try:
                duckdb_path = create_or_open_duckdb_path()
            except (exceptions.DatabaseCreationError) as error:
                error_helper(error)
                break 
            try:
                duckdb_connection = connect_to_duckdb(duckdb_path)
            except (exceptions.DuckDBDatabaseConnectionError) as error:
                error_helper(error)
                break
            try:
                create_duckdb_table(duckdb_connection)
            except (exceptions.DatabaseTableCreationError) as error:
                error_helper(error)
                break
            try:
                document_identifiers_sqlite_set = retrieve_all_document_identifiers_from_sqlite(db_connection)
            except (exceptions.DatabaseRetrievalError) as error:
                error_helper(error)
                break
            try:
                document_identifiers_duckdb_set = retrieve_all_document_identifiers_from_duckdb(duckdb_connection)
            except (exceptions.DuckDBRetrievalError) as error:
                error_helper(error)
                break
            try:
                missing_identifiers_set = compare_sqlite_and_duckdb_identifiers(document_identifiers_sqlite_set, document_identifiers_duckdb_set)
            except (exceptions.DatabaseComparisonError) as error:
                error_helper(error)
                break
            try:
                insert_missing_identifiers_into_duckdb(missing_identifiers_set, db_connection, duckdb_connection)
            except (exceptions.DatabaseInsertionError, exceptions.DatabaseRetrievalError, exceptions.NoUUIDMatch, exceptions.DuckDBInsertionError) as error:
                error_helper(error)
                break
            try:
                file_path: str = request_document()
                start_time = start_processing_time()
            except (exceptions.InvalidFileError, exceptions.InvalidFileTypeError) as error:
                error_helper(error)
                continue  # Prompt the user to select a file again
            try:
                metadata: dict[str, Any] = read_metadata(file_path)
                content: str = read_content(file_data_path=file_path)
                character_count: int = document_character_count_check(content)
                word_count: int = word_count_check(content)
                tokenizer_token_count: int = document_token_count_check(content)
            except (exceptions.InvalidFileError, exceptions.InvalidFileTypeError, exceptions.FileNotReadableError, exceptions.DocumentTooLargeError) as error:
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
                except (exceptions.OllamaAPIError, exceptions.OllamaResponseError, exceptions.DirectoryNotWritableError,) as error:
                    error_helper(error)
                    continue  # Retry Ollama processing
                break  # Exit the inner loop if no exception occurs
            final_record: dict[str, Any] = build_final_json_record(metadata, ollama_response=ollama_response, unique_id=unique_id, source_file_name=source_file_name, processing_stats=processing_stats)
            while True:
                try:
                    auto_named_file,  holding_dir, = create_ollama_output_path(source_file_name, unique_id)
                    
                    ollama_output_holding_path: Path = write_final_record_to_json(final_record, auto_file_name=auto_named_file)
                except (exceptions.DirectoryNotWritableError) as error:
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
                except (exceptions.StagedPairNotFoundError, exceptions.OriginalFileNotFoundError, exceptions.JSONFileNotFoundError) as error:
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
                except (exceptions.OriginalFileSortError, exceptions.JSONFileSortError, exceptions.FileSortRollbackError) as error:
                    error_helper(error)
                    break
                try:
                    final_record_sql = add_to_final_record(final_record, sorted_original_file_path, sorted_ollama_file_path, total_ollama_api_processing_duration, processing_duration, ai_model, model_num_ctx, max_prompt_tokens)
                    extract_record = extract_finalrecord_values_for_sqlite(final_record_sql)
                    insert_dict = insert_dict_into_sql(extract_record, db_connection) #Saved Insert variable for debugging purposes, or later use, but not used in the final code.
                except (exceptions.DatabaseInsertionError, exceptions.DatabaseTableAlterError,) as error:
                    error_helper(error)
                    break
                try:
                    analytics_dict = retrieve_doc_analytics_from_sqlite(unique_id, db_connection)
                    insert_into_duckdb = insert_doc_analytics_into_duckdb(analytics_dict, duckdb_connection) #Saved Insert variable for debugging purposes, or later use, but not used in the final code.
                except (exceptions.DuckDBInsertionError, exceptions.NoUUIDMatch, exceptions.DatabaseRetrievalError, exceptions.DuckDBRetrievalError) as error:
                    error_helper(error)
                    break
                
                print(f"Metadata: {metadata}")
                print(f"Content preview: {content[:100] if content else 'No content'}")
                break
            break  # Exit the outer loop after processing one document
        finally:
            if duckdb_connection is not None:
                try:
                    close_duckdb_connection(duckdb_connection)
                except (exceptions.DuckDBDatabaseCloseError) as error:
                    print(f"Error occurred while closing DuckDB connection: {error}")
            if db_connection is not None:
                try:
                    close_sqlite_connection(db_connection)
                except (exceptions.DatabaseCloseError) as error:
                    print(f"Error occurred while closing SQLite connection: {error}")
            if ollama_process is not None:
                try:
                    ollama_process.terminate()
                    ollama_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        ollama_process.kill()
                        ollama_process.wait()
                    except OSError as error:
                        print(f"Error occurred while killing Ollama process: {error}")
                    
                except OSError as error:
                    print(f"Error occurred while terminating Ollama process: {error}")

if __name__ == "__main__":
    main()


