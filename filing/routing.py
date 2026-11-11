from pathlib import Path
from typing import Any
import json
import shutil
from typing import Any
import exceptions

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