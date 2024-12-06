import os
from typing import List

def load_files(directory: str) -> List[str]:
    file_paths = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(".txt"):
                file_paths.append(os.path.join(root, f))
    return file_paths

def read_file_content(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
