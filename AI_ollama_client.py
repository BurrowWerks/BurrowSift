import json
import os
import time
import subprocess
from typing import Any
import requests
from requests.exceptions import RequestException
import exceptions
from AI_payload import build_AI_config_parameters, build_AI_prompt_payload, build_AI_payload_category_summary
from AI_validation import turn_json_string_to_dict, ollama_response_validation
from documents.tokens import gemma_token_count

def automatic_ollama_start() -> subprocess.Popen[bytes] | None:
    try:
        response: requests.Response = requests.get(url="http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("Ollama API is already running.")
            return None
    except RequestException:
        pass  # Ollama API is not running, proceed to start it

    try:
        ollama_env = os.environ.copy()
        ollama_env["OLLAMA_FLASH_ATTENTION"] = "1"
        ollama_env["OLLAMA_KV_CACHE_TYPE"] = "q8_0"

        ollama_process = subprocess.Popen(args=["ollama", "serve"], env=ollama_env,)
        
        for _ in range(10):  # Poll up to 10 times
            try:
                polling_response = requests.get("http://localhost:11434/api/tags", timeout=1)
                if polling_response.status_code == 200:
                    print("Ollama API started successfully.")
                    return ollama_process  # Ollama API is now running
            except RequestException:
                pass  # Continue polling
            time.sleep(1)  # Wait for 1 second before the next poll
            if ollama_process.poll() is not None:
                print("Ollama process terminated unexpectedly.")
                raise exceptions.OllamaAPIError()
        ollama_process.terminate()  # Terminate the process if it didn't start successfully
        try:
            ollama_process.wait(timeout=5)  # Wait for the process to terminate
        except subprocess.TimeoutExpired:
            ollama_process.kill()  # Force kill if it didn't terminate
            ollama_process.wait()  # Wait for the process to be killed
        raise exceptions.OllamaAPIError()
    except exceptions.OllamaAPIError:
        raise 
    except Exception as e:
        raise exceptions.OllamaAPIError() from e


def send_to_ollama_api(structured_dict: dict[str, Any], source_file_name: str, unique_id: str,) -> tuple[dict[str, Any], int, int, int, int, float, int, float, str, int, int]:
    url = "http://localhost:11434/api/generate"

    structured_dict_json = json.dumps(structured_dict, indent=4)

    prompt: str = build_AI_prompt_payload(structured_dict_json=structured_dict_json)

    ai_config = build_AI_config_parameters()

    if "ai_model" not in ai_config or "model_num_ctx" not in ai_config or "max_prompt_tokens" not in ai_config:
        raise KeyError("Missing required AI configuration keys.")

    ai_model = ai_config["ai_model"]
    model_num_ctx = ai_config["model_num_ctx"]
    max_prompt_tokens = ai_config["max_prompt_tokens"]

    if not isinstance(ai_model, str) or not isinstance(model_num_ctx, int) or not isinstance(max_prompt_tokens, int):
        raise exceptions.InvalidAIConfigError()
       
    if model_num_ctx <= 0 or max_prompt_tokens <= 0:
        raise exceptions.InvalidAIConfigError()
    
    if (model_num_ctx-max_prompt_tokens < 16384):
        raise exceptions.InvalidAIConfigError()
    
    tokens_prompt: int = gemma_token_count(text=prompt)
    if tokens_prompt > max_prompt_tokens:
        raise exceptions.DocumentTooLargeError()

    payload_category_summary: dict[str, Any] = build_AI_payload_category_summary(
        ai_model=ai_model,
        prompt=prompt,
        model_num_ctx=model_num_ctx,
    )

    try:
        response_category_summary = requests.post(url, json=payload_category_summary, timeout=(10, 300))
    except RequestException as e:
        raise exceptions.OllamaAPIError() from e

    if response_category_summary.status_code == 200:
        ollama_response_json: dict[str, Any] = response_category_summary.json() #Could Fail if the response is not valid JSON, but we are assuming it is valid JSON for now.

        prompt_tokens: int = ollama_response_json.get("prompt_eval_count", 0)
        completion_tokens: int = ollama_response_json.get("eval_count", 0)
        inference_duration: int = ollama_response_json.get("eval_duration", 0)
        inference_duration_seconds: float = inference_duration / 1000000000
        prompt_eval_duration: int = ollama_response_json.get("prompt_eval_duration", 0)
        prompt_eval_duration_seconds: float = prompt_eval_duration / 1000000000


        json_string: str = ollama_response_json["response"]


        response_data: dict[str, Any] = turn_json_string_to_dict(json_string=json_string)

        print("GEMMA RESPONSE:")
        print(json.dumps(response_data, indent=4))

        ollama_response_validation(response_dict=response_data)
        print(response_data)
        print(f"Tokenizercount: {tokens_prompt}")
        print(f"Prompt tokens used: {prompt_tokens}")
        print(f"Completion tokens used: {completion_tokens}")
        return response_data, prompt_tokens, completion_tokens, tokens_prompt, inference_duration, inference_duration_seconds, prompt_eval_duration, prompt_eval_duration_seconds, ai_model, model_num_ctx, max_prompt_tokens,
    else:
        raise exceptions.OllamaAPIError()
