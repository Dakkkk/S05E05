from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, Date, text
from sqlalchemy.orm import sessionmaker
from typing import List, Dict
from config import DB_URI

engine = create_engine(DB_URI)
Session = sessionmaker(bind=engine)
session = Session()

metadata = MetaData()

documents_table = Table(
    "documents", metadata,
    Column("id", Integer, primary_key=True),
    Column("source", String(255)),
    Column("date_created", Date),
    Column("category", String(255)),
    Column("content", Text)
)

def insert_records(records: List[Dict]):
    with engine.begin() as conn:
        conn.execute(documents_table.insert(), records)

def execute_query(sql_query: str):
    with engine.connect() as conn:
        # Wrap the raw SQL string in text() before executing
        result = conn.execute(text(sql_query))
        return result.fetchall()
