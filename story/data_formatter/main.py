import os
from utils.file_loader import load_files, read_file_content
from utils.chunker import chunk_text
from utils.llm import format_chunk_with_llm
from utils.format import parse_formatted_text
from utils.db import insert_records
from config import SOURCE_DIR, DATE_CREATED, CATEGORY, MAX_TOKENS_PER_CHUNK, LLM_MODEL

DEBUG_FILE = "debug_output.txt"

def main():
    files = load_files(SOURCE_DIR)
    doc_id_counter = 1

    # Ensure the debug file is created/cleared at the start of processing
    # If you do not want to clear it each run, remove the next two lines.
    if os.path.exists(DEBUG_FILE):
        os.remove(DEBUG_FILE)

    for fpath in files:
        source = os.path.basename(fpath)
        text = read_file_content(fpath)

        # Chunk the file content
        chunks = chunk_text(text, MAX_TOKENS_PER_CHUNK, model_name=LLM_MODEL)

        records_to_insert = []
        for chunk in chunks:
            # Get formatted text from LLM
            formatted = format_chunk_with_llm(doc_id_counter, source, DATE_CREATED, CATEGORY, chunk)
            
            # Parse into dict
            record = parse_formatted_text(formatted)
            records_to_insert.append(record)

            # For debugging: Append the formatted text to a single .txt file
            # This includes both the [METADATA] and [CONTENT] sections.
            with open(DEBUG_FILE, "a", encoding="utf-8") as dbg_file:
                dbg_file.write(formatted + "\n\n")  # Add spacing between records

            doc_id_counter += 1

        # Insert into DB
        insert_records(records_to_insert)
        print(f"Inserted {len(records_to_insert)} records from {source}")

if __name__ == "__main__":
    main()
