from requests.exceptions import RequestException


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

class DuckDBInsertionError(Exception):
    statement: str = ("Dictionary failed to pass into DuckDB database")
    def __init__(self):
        super().__init__(self.statement)

class DatabaseRetrievalError(Exception):
    statement: str = ("Failed to retrieve data from database.")
    def __init__(self):
        super().__init__(self.statement)

class DuckDBRetrievalError(Exception):
    statement: str = ("Failed to retrieve data from DuckDB database.")
    def __init__(self):
        super().__init__(self.statement)

class DatabaseComparisonError(Exception):
    statement: str = ("Failed to compare data between databases.")
    def __init__(self):
        super().__init__(self.statement)

class DatabaseCloseError(Exception):
    statement: str = ("Failed to close database connection.")
    def __init__(self):
        super().__init__(self.statement)

class DuckDBDatabaseCloseError(Exception):
    statement: str = ("Failed to close DuckDB database connection.")
    def __init__(self):
        super().__init__(self.statement)

class OllamaCloseError(Exception):
    statement: str = ("Failed to close Ollama process.")
    def __init__(self):
        super().__init__(self.statement)
class InvalidAIConfigError(Exception):
    statement: str = ("Invalid AI configuration.")
    def __init__(self):
        super().__init__(self.statement)