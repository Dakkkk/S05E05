from openai import OpenAI
from config import OPENAI_API_KEY, LLM_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

def format_chunk_with_llm(doc_id: int, source: str, date_created: str, category: str, chunk_text: str) -> str:
    prompt = f"""
You are given a chunk of text from a document.

Please format it into the following structure:

[METADATA]
id: {doc_id}
source: {source}
date_created: {date_created}
category: {category}

[CONTENT]
{chunk_text}

Return only this structure.
"""
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=1500
    )
    return response.choices[0].message.content.strip()
