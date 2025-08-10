"""
WhatDataIAmGiving - Terms & Conditions Scraper API
A FastAPI application that scrapes website Terms & Conditions
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import settings
from app.cors import setup_cors
from app.routes import terms_router
from app.database import init_mongodb, close_mongodb

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting up WhatDataIAmGiving API...")
    
    # Initialize MongoDB connection
    if init_mongodb():
        logger.info("MongoDB connection established")
    else:
        logger.warning("MongoDB connection failed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down WhatDataIAmGiving API...")
    close_mongodb()
    logger.info("Shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Setup CORS
setup_cors(app)

# Include routers
app.include_router(terms_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)