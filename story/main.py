import os
from questions import QUESTIONS
from utils.logger import log_message
from utils.llm_postgres_expert import get_db_query_from_question
from utils.db import execute_query
from utils.llm_question_answerer import answer_question_in_polish

def main():
    # Clear the debug log before we start (optional)
    if os.path.exists("logs/debug_output.txt"):
        os.remove("logs/debug_output.txt")

    for idx, question in enumerate(QUESTIONS, start=1):
        log_message(f"📝 Processing question #{idx}: {question}")
        
        # Step 1: Get SQL query from LLM (postgres expert)
        sql_query = get_db_query_from_question(question)
        log_message(f"🤖 Postgres Expert Query for Q#{idx}: {sql_query}")

        # Step 2: Execute SQL query to get data
        results = []  # Initialize results as an empty list by default.
        context_text = ""
        try:
            results = execute_query(sql_query)
        except Exception as e:
            # If the query fails, log and continue
            log_message(f"❌ Error executing query for Q#{idx}: {str(e)}")
        else:
            # Convert results to a context string
            context_texts = []
            for row in results:
                # row = (id, source, date_created, category, content)
                context_texts.append(row[-1])  # content is last
            context_text = "\n\n---\n\n".join(context_texts)

        log_message(f"📜 Retrieved {len(results)} rows for Q#{idx}")

        # Step 3: Use QA LLM with the provided context
        answer = answer_question_in_polish(question, context_text)
        log_message(f"🗣 Answer for Q#{idx}: {answer}")

        # Add a blank line after each question to separate logs
        log_message("----------")

if __name__ == "__main__":
    main()
