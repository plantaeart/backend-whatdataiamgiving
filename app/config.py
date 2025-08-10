"""
Configuration settings for WhatDataIAmGiving API
"""

import logging
import os
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
    
    # Enhanced scraping configuration
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    
    # Browser-like headers
    DEFAULT_HEADERS: dict = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0"
    }
    
    # AI Configuration
    @property
    def GEMINI_API_KEY(self) -> str:
        return os.getenv("GEMINI_API_KEY", "")
    
    GEMINI_MODEL: str = "gemini-2.0-flash"
    AI_TIMEOUT: float = 60.0
    
    # Terms & Conditions patterns to search for (English and French) - PERMISSIVE
    TERMS_PATTERNS: List[str] = [
        # Basic patterns - catch most terms pages
        r'terms',
        r'conditions',
        r'privacy',
        r'legal',
        r'policy',
        r'agreement',
        r'notice',
        
        # French patterns
        r'conditions',
        r'cgu',
        r'cgv', 
        r'politique',
        r'mentions',
        r'données',
        r'juridique',
        r'légal',
        r'confidentialité',
        r'cookies',
        r'protection',
        r'accord',
        r'utilisation'
    ]
    
    # Only exclude very specific problematic content
    EXCLUDE_PATTERNS: List[str] = [
        r'report.*illegal.*content',
        r'help.*center',
        r'customer.*service',
        r'contact.*us',
        r'careers',
        r'jobs',
        r'about.*us'
    ]
    
    # Logging configuration
    LOG_LEVEL: int = logging.INFO


# Create settings instance
settings = Settings()
