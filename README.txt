# Story Investigation System

A comprehensive system for investigating and analyzing stories using AI-powered tools, web crawling, and database operations.

## System Components

- Web crawler for data collection
- PostgreSQL database for data storage
- LLM-powered question answering
- Document analysis and processing

## Database Setup

1. Install PostgreSQL (choose one method):
   
   Using Homebrew:
   ```
   brew install postgresql@15
   brew services start postgresql@15
   ```
   
   OR using Postgres.app:
   - Download from https://postgresapp.com/
   - Drag to Applications folder and start

2. Create Database and User:
   ```
   psql postgres
   CREATE DATABASE story_investigation;
   CREATE USER username WITH PASSWORD 'password';
   GRANT ALL PRIVILEGES ON DATABASE story_investigation TO username;
   ```

3. Configure Environment Variables:
   Add to `story/.env`:
   ```
   DB_USER=username
   DB_PASS=password
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=story_investigation
   ```

4. Install requirements:
   ```
   pip install -r requirements.txt
   ```  

## Workflow

1. Data Collection & Processing:
   - Run `story/data_formatter/main.py` first to populate the database
   - Data is extracted from raw files and structured in PostgreSQL

2. Question Answering:
   - Run `story/main.py` to process questions
   - System follows a multi-step approach:
     a. LLM generates PostgreSQL query based on question
     b. Another LLM formulates answer using database results
     c. Fallback to raw document analysis if needed
     d. Web crawler activation for questions 3-5
     e. Results saved to answers.json

## Web Crawler Usage

The SmartWebCrawler can be used independently: