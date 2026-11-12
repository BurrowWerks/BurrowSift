import json
from typing import Any
import exceptions

def turn_json_string_to_dict(json_string: str) -> dict[str, Any]:
    try:
        response_dict: dict[str, Any] = json.loads(json_string)
        return response_dict
    except json.JSONDecodeError as e:
        raise exceptions.OllamaResponseDecodingError() from e

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