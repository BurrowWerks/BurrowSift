from transformers import AutoTokenizer, PreTrainedTokenizerBase
from typing import cast
import constants
import exceptions

tokenizer: PreTrainedTokenizerBase = cast(
    PreTrainedTokenizerBase,
    AutoTokenizer.from_pretrained(# pyright: ignore[reportUnknownMemberType]
        pretrained_model_name_or_path="google/gemma-4-12B"
    ),
)

def gemma_token_count(text: str) -> int:
    token_ids: list[int] = tokenizer.encode( # pyright: ignore[reportUnknownMemberType]
        text,
        add_special_tokens=False,
    )
    return len(token_ids)

def document_token_count_check(content: str) -> int:
    document_token_count: int = gemma_token_count(content)
    print(document_token_count)
    if document_token_count > constants.MAX_DOCUMENT_TOKENS:
        raise exceptions.DocumentTooLargeError()
    return document_token_count