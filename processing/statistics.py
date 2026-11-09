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