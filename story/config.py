import os
from dotenv import load_dotenv
from datetime import date

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# We expect DB credentials from .env as well
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "story_database")

DB_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Model names
POSTGRES_EXPERT_MODEL = "gpt-4o-mini"   # LLM acting as SQL/DB expert
QA_MODEL = "gpt-4o-mini"                # LLM answering questions in Polish

LOG_FILE = "logs/debug_output.txt"
