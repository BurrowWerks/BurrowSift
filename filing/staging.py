from pathlib import Path
import exceptions


def create_ollama_output_path(source_file_name: str, unique_id: str,)  -> tuple[Path, Path]:
    holding_dir: Path = Path(r"B:\Development\Projects\Learning\Python\BurrowSift\Holding")
    holding_dir.mkdir(parents=True, exist_ok=True)
    auto_file_name: Path = holding_dir / f"{source_file_name}__{unique_id}.json"
    path_tuple = (auto_file_name, holding_dir)
    return path_tuple

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