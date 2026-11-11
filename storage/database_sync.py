from storage.sqlite_storage import retrieve_doc_analytics_from_sqlite
from storage.duckdb_store import insert_doc_analytics_into_duckdb
import sqlite3
import duckdb
from typing import Any

def compare_sqlite_and_duckdb_identifiers(sqlite_identifiers: set[str], duckdb_identifiers: set[str]) -> set[str]:
    missing_in_duckdb = sqlite_identifiers - duckdb_identifiers
    return missing_in_duckdb

def insert_missing_identifiers_into_duckdb(missing_identifiers: set[str], db_connection: sqlite3.Connection, duckdb_connection: duckdb.DuckDBPyConnection) -> None:
    for unique_id in missing_identifiers:
        missing_analytics_dict: dict[str, Any] = dict[str, Any](retrieve_doc_analytics_from_sqlite(unique_id, db_connection))
        insert_doc_analytics_into_duckdb(missing_analytics_dict, duckdb_connection=duckdb_connection)