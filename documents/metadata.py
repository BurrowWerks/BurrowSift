from os import stat_result
from pathlib import Path
from typing import Any

import exceptions

def read_metadata(file_path: str) -> dict[str, Any]:
    if not Path(file_path).is_file(): 
        raise exceptions.InvalidFileError()
    file_data_path = Path(file_path)
    file_data_stat: stat_result = file_data_path.stat()
    metadata: dict[str, Any] = {"file_name": file_data_path.name,
                                "file_size": file_data_stat.st_size,
                                "file_type": file_data_path.suffix,
                                "last_modified": file_data_stat.st_mtime,
                                "created": file_data_stat.st_birthtime,
                                "absolute_path": str(object=file_data_path.resolve())}
    return metadata