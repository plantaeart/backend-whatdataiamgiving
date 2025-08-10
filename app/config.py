"""
Configuration settings for WhatDataIAmGiving API
"""

import logging
from typing import List


class Settings:
    # API Configuration
    APP_NAME: str = "WhatDataIAmGiving API"
    APP_DESCRIPTION: str = "Scrape Terms & Conditions from websites"
    APP_VERSION: str = "1.0.0"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Request Configuration
    REQUEST_TIMEOUT: float = 30.0
    MAX_TERMS_PAGES: int = 3
    MIN_CONTENT_LENGTH: int = 100
    
    # User Agent for web scraping
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Terms & Conditions patterns to search for
    TERMS_PATTERNS: List[str] = [
        r'terms.*conditions?',
        r'privacy.*policy',
        r'user.*agreement',
        r'terms.*service',
        r'terms.*use',
        r'legal.*notice',
        r'data.*policy',
        r'cookie.*policy'
    ]
    
    # Logging configuration
    LOG_LEVEL: int = logging.INFO


# Create settings instance
settings = Settings()
