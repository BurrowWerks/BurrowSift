import time

def document_character_count_check(content: str) -> int:
    character_count: int = len(content)
    return character_count

def word_count_check(content: str) -> int:
    word_count: int = len(content.split())
    return word_count

def start_processing_time():
    processing_time_start = time.perf_counter()
    return processing_time_start

def end_processing_time():
    processing_time_end = time.perf_counter()
    return processing_time_end

def calc_total_processing_time(processing_time_start: float, processing_time_end: float) -> float:
    processing_duration = processing_time_end - processing_time_start
    return processing_duration

def build_processing_stats(character_count:int, word_count:int, tokenizer_token_count:int, prompt_tokens:int, completion_tokens:int, tokens_prompt: int, inference_duration: int, inference_duration_seconds: float, prompt_eval_duration: int, prompt_eval_duration_seconds: float) -> dict[str, int|float]:
    processing_stats: dict[str, int|float] = {"character_count": character_count, "word_count": word_count, "tokenizer_token_count": tokenizer_token_count, "tokens_prompt": tokens_prompt, "prompt_eval_count": prompt_tokens, "eval_count": completion_tokens, "inference_duration": inference_duration, "inference_duration_seconds": inference_duration_seconds, "prompt_eval_duration": prompt_eval_duration, "prompt_eval_duration_seconds": prompt_eval_duration_seconds}
    return processing_stats