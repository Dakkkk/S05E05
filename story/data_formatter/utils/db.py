from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, Date
from sqlalchemy.orm import sessionmaker
from typing import List, Dict
from config import DB_URI

engine = create_engine(DB_URI)
Session = sessionmaker(bind=engine)
session = Session()

metadata = MetaData()

# Example table definition; adjust to your needs
# Make sure this table is already created in your DB,
# or uncomment metadata.create_all(engine) if you want to create it from code.
documents_table = Table(
    "documents", metadata,
    Column("id", Integer, primary_key=True),
    Column("source", String(255)),
    Column("date_created", Date),
    Column("category", String(255)),
    Column("content", Text)
)

metadata.create_all(engine)  # Uncomment if needed to create the table

def insert_records(records: List[Dict]):
    """
    Insert a list of records into the database.
    Each record is expected to have keys:
    id, source, date_created, category, content
    """
    with engine.begin() as conn:
        conn.execute(documents_table.insert(), records)
