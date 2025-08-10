"""
Terms and Conditions API routes
"""

import logging
from fastapi import APIRouter, HTTPException

from ..models import TermsRequest, TermsResponse, TermsCheckResponse
from ..utils import TermsAndConditionUtils

logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter(
    prefix="/api",
    tags=["Terms & Conditions"]
)

# Initialize utils
terms_utils = TermsAndConditionUtils()


@router.get("/")
def read_root():
    """Root endpoint with API information"""
    return {
        "message": "WhatDataIAmGiving API",
        "description": "Scrape Terms & Conditions from websites",
        "endpoints": {
            "check_terms": "/api/check-terms",
            "scrape_terms": "/api/scrape-terms", 
            "docs": "/docs",
            "health": "/api/health"
        }
    }


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "terms-scraper"}


@router.post("/check-terms", response_model=TermsCheckResponse)
async def check_terms_exist(request: TermsRequest):
    """
    Check if a website has Terms & Conditions pages
    
    - **url**: Website URL to check
    """
    try:
        result = await terms_utils.check_terms_exist(url=str(request.url))
        
        if result.error:
            raise HTTPException(status_code=400, detail=result.error)
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/scrape-terms", response_model=TermsResponse)
async def scrape_terms(request: TermsRequest):
    """
    Scrape Terms & Conditions content from a website URL
    
    - **url**: Website URL to scrape
    """
    try:
        result = await terms_utils.scrape_website_terms(url=str(request.url))
        
        if result.error:
            raise HTTPException(status_code=400, detail=result.error)
            
        if not result.extracted_text:
            raise HTTPException(
                status_code=404, 
                detail="No Terms & Conditions content found on the website"
            )
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
