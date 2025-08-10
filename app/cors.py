"""
CORS (Cross-Origin Resource Sharing) configuration
"""

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI


def setup_cors(app: FastAPI) -> None:
    """
    Configure CORS middleware for the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:4200",      # Angular dev server
            "http://127.0.0.1:4200",     # Alternative localhost
            "http://localhost:3000",      # React dev server (if needed)
            "http://127.0.0.1:3000",     # Alternative localhost for React
        ],
        allow_credentials=True,
        allow_methods=["*"],              # Allow all HTTP methods
        allow_headers=["*"],              # Allow all headers
    )
