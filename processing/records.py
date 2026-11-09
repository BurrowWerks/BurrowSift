
from typing import Any
from pathlib import Path

def build_structured_content(metadata: dict[str, Any], content: str) -> dict[str, Any]:
    structured_dict: dict[str, dict[str, Any]] = {"metadata": metadata, 
                                                  "doc_content": {"content": content
                                                                  }}
    return structured_dict

def build_final_json_record(metadata: dict[str, Any], ollama_response: dict[str, Any], unique_id: str, source_file_name: str, processing_stats:dict[str, int| float]) -> dict[str, Any]:
    final_record: dict[str, Any] = {
        "metadata": metadata,
        "document_identifier": unique_id,
        "processing_stats": processing_stats,
        "source_file_name": source_file_name,
        "ollama_response": ollama_response,   
    }
    return final_record

def add_to_final_record(final_record: dict[str, Any], sorted_original_file_path: Path, sorted_ollama_file_path: Path, total_ollama_processing_duration: float, total_doc_processing_duration: float, ai_model: str, model_num_ctx: int, max_prompt_tokens: int) -> dict[str, Any]:
    final_record["current_file_path"] = str(sorted_original_file_path)
    final_record["json_file_path"] = str(sorted_ollama_file_path)
    final_record["total_ollama_processing_duration"] = total_ollama_processing_duration
    final_record["total_doc_processing_duration"] = total_doc_processing_duration
    final_record["ai_model"] = ai_model
    final_record["model_max_tokens"] = model_num_ctx
    final_record["max_processing_tokens"] = max_prompt_tokens
    return final_record