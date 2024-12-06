import os
import asyncio
from questions import QUESTIONS
from utils.logger import log_message
from utils.llm_postgres_expert import get_db_query_from_question
from utils.db import execute_query
from utils.llm_question_answerer import answer_question_in_polish
from config import QA_MODEL, OPENAI_API_KEY
from openai import OpenAI
from pathlib import Path
from tools.web_crawler import WebCrawler

client = OpenAI(api_key=OPENAI_API_KEY)

FALLBACK_CONTEXT_PATH = "data/all_information.txt"

def answer_question_with_all_info(question: str) -> str:
    # Load fallback context from a single large text file
    if os.path.exists(FALLBACK_CONTEXT_PATH):
        with open(FALLBACK_CONTEXT_PATH, "r", encoding="utf-8") as f:
            all_info_context = f.read()
    else:
        all_info_context = ""

    prompt = f"""
Jesteś ekspertem od tej historii i potrafisz odpowiadać na pytania na podstawie dostarczonego szerszego kontekstu.

Oto pytanie:
"{question}"

Oto kontekst (pełne informacje):
{all_info_context}

Odpowiedz po polsku, na podstawie podanego kontekstu. Jeżeli nadal nie możesz znaleźć odpowiedzi, wyraźnie powiedz, że brakuje informacji i określ, jakiego rodzaju informacji brakuje.
"""
    response = client.chat.completions.create(
        model="gpt-4o",  # or your chosen model with large context window
        messages=[
            {"role": "system", "content": "Jesteś pomocnym asystentem o zwiększonym limicie tokenów."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.001,
        max_tokens=10000
    )
    return response.choices[0].message.content.strip()

async def use_web_crawler(question: str, question_id: str) -> str:
    # Adjust base_url and storage_dir as needed
    base_url = "https://softo.ag3nts.org"  # Replace with a suitable base URL
    storage_dir = Path("crawler_storage")
    crawler = WebCrawler(base_url=base_url, storage_dir=storage_dir)

    answer = await crawler.crawl(question, question_id, max_depth=3)
    return answer if answer else "Brakuje informacji. Nie znaleziono odpowiedzi w trakcie crawlowania."

def main():
    # Clear the debug log before we start (optional)
    if os.path.exists("logs/debug_output.txt"):
        os.remove("logs/debug_output.txt")

    for idx, question in enumerate(QUESTIONS, start=1):
        log_message(f"📝 Processing question #{idx}: {question}")

        # For questions #3, #4, and #5 we use ONLY the web crawler
        if idx in [3, 4, 5]:
            log_message(f"🌐 Using web crawler for Q#{idx}")
            # Run the crawler asynchronously
            answer = asyncio.run(use_web_crawler(question, str(idx)))
            log_message(f"🗣 Answer for Q#{idx} (WebCrawler): {answer}")
            log_message("----------")
            continue

        # For all other questions, the old logic remains

        # Step 1: Get SQL query from LLM (postgres expert)
        sql_query = get_db_query_from_question(question)
        log_message(f"🤖 Postgres Expert Query for Q#{idx}: {sql_query}")

        # Step 2: Execute SQL query to get data
        results = []
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

        # Step 3: Use QA LLM with the provided context from the DB
        answer = answer_question_in_polish(question, context_text)
        log_message(f"🗣 Answer for Q#{idx} (DB-based): {answer}")

        # Check if the answer indicates missing information
        if "Brakuje informacji" in answer or "brakuje informacji" in answer:
            # Attempt fallback with all_information.txt
            log_message(f"🔎 Fallback: Trying to find answer in all_information.txt for Q#{idx}")
            fallback_answer = answer_question_with_all_info(question)
            log_message(f"🗣 Answer for Q#{idx} (Fallback): {fallback_answer}")

        log_message("----------")


if __name__ == "__main__":
    main()
