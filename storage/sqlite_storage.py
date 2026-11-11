import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Any

import exceptions

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

def close_sqlite_connection(db_connect: sqlite3.Connection) -> None:
    try:
        db_connect.close()
    except (sqlite3.Error) as e:
        raise exceptions.DatabaseCloseError() from e

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