# story/utils/llm_postgres_expert.py

from pydantic import BaseModel
from openai import OpenAI
from config import OPENAI_API_KEY, POSTGRES_EXPERT_MODEL

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

class SQLQuery(BaseModel):
    sql_query: str

def get_db_query_from_question(question: str) -> str:
    # Prompt to the model: explain what we want and how we want the output
    prompt = f"""
You are a PostgreSQL expert. You have a table named "documents" with columns (id, source, date_created, category, content).
The content column holds large text chunks about a story involving time travel, characters like Rafał, Andrzej Maj, Zygfryd, and so forth.

Given the question:
"{question}"

Produce a SQL SELECT statement that retrieves ALL rows from 'documents' that might contain relevant information to answer this question.
Use ILIKE conditions on 'content' to find rows related to the question.

Return your answer as a JSON object that strictly follows this schema:

```json
{{
  "sql_query": "<SQL query string>"
}}
"""
    # Call the OpenAI API using the parse functionality for structured outputs
    completion = client.beta.chat.completions.parse(
    model=POSTGRES_EXPERT_MODEL,
    messages=[
        {"role": "system", "content": "You are a helpful assistant who is expert in SQL."},
        {"role": "user", "content": prompt}
    ],
    response_format=SQLQuery,
    temperature=0,
        max_tokens=1000
    )
    parsed_response = completion.choices[0].message.parsed
    return parsed_response.sql_query