import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()

# Assumes you have an OpenAI API key set as an environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# LLM model configuration
LLM_MODEL = "gpt-4o-mini" #NEVER CHANGE THIS

# Directory containing the .txt files
SOURCE_DIR = "data"

DATE_CREATED = date.today().isoformat()
CATEGORY = "technical_docs"  # You can adjust or add logic to determine category

# Database configuration: update with your credentials
DB_URI = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

# Chunking parameters
MAX_TOKENS_PER_CHUNK = 2000   # Adjust as needed
