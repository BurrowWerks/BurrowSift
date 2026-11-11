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
import duckdb
from AI_payload import build_AI_config_parameters, build_AI_payload_category_summary, build_AI_prompt_payload
import exceptions
from storage.sqlite_storage import create_or_open_database, connect_sqlite, create_db_table, alter_update_sqlite_table, close_sqlite_connection, extract_finalrecord_values_for_sqlite, insert_dict_into_sql, retrieve_doc_analytics_from_sqlite, retrieve_all_document_identifiers_from_sqlite
from storage.duckdb_store import create_or_open_duckdb_path, connect_to_duckdb, create_duckdb_table, close_duckdb_connection, insert_doc_analytics_into_duckdb, retrieve_all_document_identifiers_from_duckdb
from storage.database_sync import compare_sqlite_and_duckdb_identifiers, insert_missing_identifiers_into_duckdb
from filing.staging import create_ollama_output_path, pair_identity, pair_contents_validation
from filing.routing import routing_destination, build_destination_path, move_paired_files
from documents.metadata import read_metadata
from documents.readers import read_content
from documents.tokens import document_token_count_check, gemma_token_count
from processing.statistics import document_character_count_check, word_count_check, start_processing_time, end_processing_time, calc_total_processing_time
from processing.records import build_structured_content, build_final_json_record, add_to_final_record
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
                start_time: float = start_processing_time()
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


