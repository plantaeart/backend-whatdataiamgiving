"""
WhatDataIAmGiving - Terms & Conditions Scraper API
A FastAPI application that scrapes website Terms & Conditions
"""

import logging
from fastapi import FastAPI

from app.config import settings
from app.cors import setup_cors
from app.routes import terms_router

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup CORS
setup_cors(app)

# Include routers
app.include_router(terms_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)