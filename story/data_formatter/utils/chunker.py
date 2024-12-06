from typing import List
import tiktoken

def chunk_text(text: str, max_tokens: int, model_name: str = "gpt-4o-mini") -> List[str]:
    enc = tiktoken.encoding_for_model(model_name)
    tokens = enc.encode(text)
    
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_str = enc.decode(chunk_tokens)
        chunks.append(chunk_str)
        start = end
    return chunks
