"""
Terms and Conditions API routes
"""

import logging
from urllib.parse import urlparse, urlunparse
from fastapi import APIRouter, HTTPException

from ..models import TermsRequest, TermsCheckResponse
from ..models.ai_analysis_response import AIAnalysisResponse, AnalyzeTermsRequest
from ..utils.terms_and_condition_utils import TermsAndConditionUtils
from ..services.ai_analysis import ai_service

logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter(
    prefix="/api",
    tags=["Terms & Conditions"]
)

# Initialize utils
terms_utils = TermsAndConditionUtils()


def normalize_url(url: str) -> str:
    """
    Normalize URL by adding 'www.' if missing
    
    Examples:
    - https://example.com → https://www.example.com
    - http://example.com → http://www.example.com
    - https://www.example.com → https://www.example.com (unchanged)
    - https://subdomain.example.com → https://subdomain.example.com (unchanged)
    """
    try:
        parsed = urlparse(url)
        
        # Only add www. if:
        # 1. URL doesn't already have www.
        # 2. Domain doesn't have a subdomain (no dots before the main domain)
        netloc = parsed.netloc.lower()
        
        if not netloc.startswith('www.') and netloc.count('.') == 1:
            # Add www. to the domain
            new_netloc = f"www.{netloc}"
            new_parsed = parsed._replace(netloc=new_netloc)
            normalized_url = urlunparse(new_parsed)
            logger.info(f"📝 Normalized URL: {url} → {normalized_url}")
            return normalized_url
        
        return url
        
    except Exception as e:
        logger.warning(f"Failed to normalize URL {url}: {str(e)}")
        return url


@router.get("/")
def read_root():
    """Root endpoint with API information"""
    return {
        "message": "WhatDataIAmGiving API",
        "description": "Scrape Terms & Conditions from websites",
        "endpoints": {
            "find_terms": "/api/find-terms",
            "analyze_terms": "/api/analyze-terms",
            "docs": "/docs",
            "health": "/api/health"
        }
    }


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "terms-scraper"}


@router.post("/find-terms", response_model=TermsCheckResponse)
async def find_terms(request: TermsRequest):
    """
    Find Terms & Conditions pages on a website
    
    This endpoint scans a website to locate Terms & Conditions, Privacy Policy,
    and Cookie Policy pages. Returns all found URLs without content analysis.
    Automatically normalizes URLs by adding 'www.' if missing.
    
    **What it does:**
    - Normalizes input URL (adds www. if missing)
    - Scans the website for terms-related links
    - Follows redirects to get final URLs
    - Returns list of found terms pages
    - No AI analysis or content extraction
    
    **Use cases:**
    - Quick check if a site has terms pages
    - Get URLs before full AI analysis
    - Batch processing of multiple sites
    
    - **url**: Website URL to scan for terms pages (will be normalized)
    """
    try:
        # Normalize the URL first
        normalized_url = normalize_url(str(request.url))
        logger.info(f"🔍 Finding terms for URL: {normalized_url}")
        
        result = await terms_utils.check_terms_exist(url=normalized_url)
        
        if result.error:
            raise HTTPException(status_code=400, detail=result.error)
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/analyze-terms", response_model=AIAnalysisResponse)
async def analyze_terms_with_ai(request: AnalyzeTermsRequest):
    """
    Analyze Terms & Conditions using AI
    
    **Process Flow:**
    1. Find Terms & Conditions URLs (no AI cost)
    2. Only if terms found → call AI for analysis
    3. Return detailed privacy assessment with data buyers list
    
    This endpoint provides detailed privacy analysis with:
    
    **Privacy Score (0-100):**
    - 90-100: Excellent privacy protection
    - 70-89: Good privacy protection 
    - 50-69: Moderate privacy protection
    - 30-49: Poor privacy protection
    - 0-29: Very poor privacy protection
    
    **Categorized Analysis:**
    - OK: Good privacy practices
    - NEUTRAL: Standard industry practices  
    - BAD: Concerning privacy practices
    
    **Data Buyers Identification:**
    - Lists specific companies or types of buyers if data is sold
    - Includes advertising networks, data brokers, marketing companies
    - Named business partners and subsidiaries
    
    **Analysis Method:**
    - URL: AI directly accesses the terms page (faster, cheaper)
    - Text: Fallback text extraction (if URL fails)
    
    - **url**: Website URL to analyze (will be normalized)
    """
    try:
        # Normalize the URL first
        normalized_url = normalize_url(str(request.url))
        
        # First, find the terms & conditions URLs using our find-terms logic
        logger.info(f"🔍 Finding terms URLs for: {normalized_url}")
        terms_result = await terms_utils.check_terms_exist(url=normalized_url)
        
        if terms_result.error:
            logger.error(f"❌ Error finding terms: {terms_result.error}")
            raise HTTPException(status_code=400, detail=terms_result.error)
            
        # Early exit if no terms found - NO AI CALL MADE
        if not terms_result.has_terms or not terms_result.found_terms_pages:
            logger.info(f"❌ No terms found for {normalized_url} - skipping AI analysis")
            raise HTTPException(
                status_code=404, 
                detail="No Terms & Conditions pages found on the website. Cannot perform AI analysis."
            )
        
        # Only proceed with AI analysis if we found terms pages
        terms_url = terms_result.found_terms_pages[0]
        logger.info(f"✅ Terms found! Starting AI analysis of: {terms_url}")
        
        # Try AI analysis by URL first (faster, cheaper)
        analysis = await ai_service.analyze_terms_by_url(terms_url)
        analysis_method = "url"
        
        # If URL analysis failed, try text extraction fallback
        if not analysis:
            logger.info("URL analysis failed, trying text extraction fallback")
            try:
                # Extract text from the terms page
                text_content = await _extract_terms_text(terms_url)
                if text_content:
                    analysis = await ai_service.analyze_terms_by_text(text_content, terms_url)
                    analysis_method = "text"
                else:
                    analysis_method = "failed"
            except Exception as e:
                logger.error(f"Text extraction failed: {str(e)}")
                analysis_method = "failed"
        
        # Parse the analysis into structured format
        structured_analysis = None
        raw_analysis = None  # Only set when structured parsing fails
        
        if analysis and isinstance(analysis, dict):
            try:
                from ..models.ai_analysis_response import DetailedAIAnalysis, TermsAnalysis
                
                # Ensure all required fields exist
                if "privacy_score" in analysis:
                    terms_analysis_data = analysis.get("terms_analysis", {})
                    structured_analysis = DetailedAIAnalysis(
                        privacy_score=analysis.get("privacy_score", 50),
                        score_explanation=analysis.get("score_explanation", "No explanation provided"),
                        terms_analysis=TermsAnalysis(
                            ok=terms_analysis_data.get("ok", []),
                            neutral=terms_analysis_data.get("neutral", []),
                            bad=terms_analysis_data.get("bad", [])
                        ),
                        data_selling=analysis.get("data_selling", "Information not available"),
                        data_buyers=analysis.get("data_buyers", []),
                        data_storage=analysis.get("data_storage", "Information not available"),
                        main_concerns=analysis.get("main_concerns", []),
                        user_rights=analysis.get("user_rights", "Information not available"),
                        summary=analysis.get("summary", "No summary available")
                    )
                    logger.info("AI Service: Successfully parsed structured analysis")
                else:
                    logger.warning("AI Service: Missing privacy_score in analysis, keeping raw")
                    raw_analysis = analysis  # Keep raw when missing required fields
            except Exception as e:
                logger.error(f"Error structuring analysis: {str(e)}")
                raw_analysis = analysis  # Keep raw analysis as fallback when parsing fails
        elif analysis:
            logger.warning("AI Service: Analysis is not a dict, keeping raw")
            raw_analysis = analysis  # Keep raw when not a dict
        
        return AIAnalysisResponse(
            url=str(request.url),
            terms_urls=terms_result.found_terms_pages,
            analysis=structured_analysis,
            raw_analysis=raw_analysis,  # Only present when structured parsing fails
            analysis_method=analysis_method,
            error=None if analysis else "AI analysis failed"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in AI analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def _extract_terms_text(url: str) -> str:
    """Helper function to extract text from a terms page"""
    import httpx
    from bs4 import BeautifulSoup
    from ..config import settings
    
    try:
        async with httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers={'User-Agent': settings.USER_AGENT}
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Extract clean text
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # Get clean text
            text = soup.get_text(separator=' ', strip=True)
            return text
            
    except Exception as e:
        logger.error(f"Error extracting text from {url}: {str(e)}")
        return ""
