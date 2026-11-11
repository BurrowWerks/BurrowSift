import duckdb
from pathlib import Path
from typing import Any

import exceptions

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


def close_duckdb_connection(duckdb_connect: duckdb.DuckDBPyConnection) -> None:
    try:
        duckdb_connect.close()
    except (duckdb.Error) as e:
        raise exceptions.DuckDBDatabaseCloseError() from e

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