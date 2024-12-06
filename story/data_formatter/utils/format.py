import re
from typing import Dict

def parse_formatted_text(formatted_text: str) -> Dict:
    metadata_pattern = r"\[METADATA\].*?id:\s*(\S+).*?source:\s*(\S+).*?date_created:\s*(\S+).*?category:\s*(\S+)"
    content_pattern = r"\[CONTENT\](.*)"

    metadata_match = re.search(metadata_pattern, formatted_text, re.DOTALL)
    content_match = re.search(content_pattern, formatted_text, re.DOTALL)

    if not metadata_match or not content_match:
        raise ValueError("Formatted text does not match expected pattern.")

    doc_id = int(metadata_match.group(1))
    source = metadata_match.group(2)
    date_created = metadata_match.group(3)
    category = metadata_match.group(4)
    content = content_match.group(1).strip()

    return {
        "id": doc_id,
        "source": source,
        "date_created": date_created,
        "category": category,
        "content": content
    }
