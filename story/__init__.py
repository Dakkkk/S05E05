"""
Story package - AI-powered investigation and analysis system.

This package contains modules for:
- Web crawling and data collection (tools/)
- Data formatting and processing (data_formatter/)
- Database operations and utilities (utils/)
- Question answering and analysis
"""

from pathlib import Path

# Define important project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
CRAWLER_STORAGE = PROJECT_ROOT / "crawler_storage"
RAW_DATA = PROJECT_ROOT.parent / "raw_data"

# Ensure required directories exist
DATA_DIR.mkdir(exist_ok=True)
CRAWLER_STORAGE.mkdir(exist_ok=True)

__version__ = "0.1.0"
__author__ = "Your Name"

# Make commonly used modules available at package level
from .tools.web_crawler import SmartWebCrawler