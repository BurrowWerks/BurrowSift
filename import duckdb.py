import duckdb

conn = duckdb.connect(r"B:\BurrowSift\Database\burrowsift.analytics.duckdb")

print(conn.execute("SHOW TABLES").fetchall())

print(
    conn.execute(
        "DESCRIBE document_analytics"
    ).fetchall()
)

conn.close()