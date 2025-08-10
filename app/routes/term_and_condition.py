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
from ..services.analysis_cache import get_cache_service
from ..database import get_mongodb

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
    Normalize URL to root domain, removing tracking parameters and paths
    
    Examples:
    - https://example.com/some/path?param=value → https://www.example.com
    - https://www.amazon.fr/?&linkCode=ll2&tag=vivfr-21 → https://www.amazon.fr
    - http://example.com → http://www.example.com
    - amazon.fr → https://www.amazon.fr (adds scheme and www)
    - https://subdomain.example.com → https://subdomain.example.com (unchanged)
    """
    try:
        # If URL doesn't have a scheme, add https://
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        parsed = urlparse(url)
        
        # Clean up the netloc (remove tracking, keep subdomain structure)
        netloc = parsed.netloc.lower()
        
        # Only add www. if:
        # 1. URL doesn't already have www.
        # 2. Domain doesn't have a subdomain (no dots before the main domain)
        if not netloc.startswith('www.') and netloc.count('.') == 1:
            # Add www. to the domain
            netloc = f"www.{netloc}"
        
        # Create clean root URL (no path, no query parameters, no fragments)
        clean_url = urlunparse((
            parsed.scheme,      # Keep original scheme (http/https)
            netloc,            # Cleaned netloc
            '',                # Remove path
            '',                # Remove params
            '',                # Remove query
            ''                 # Remove fragment
        ))
        
        logger.info(f"📝 Normalized URL: {url} → {clean_url}")
        return clean_url
        
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
            "list_analyses": "/api/analysis",
            "get_analysis": "/api/analysis/{url}",
            "delete_analysis": "/api/analysis/{url} (DELETE)",
            "clear_expired": "/api/analysis (DELETE)",
            "health": "/api/health",
            "mongodb_health": "/api/mongodb-health",
            "docs": "/docs"
        }
    }


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "terms-scraper"}


@router.get("/mongodb-health")
def mongodb_health():
    """MongoDB connectivity check"""
    mongodb = get_mongodb()
    
    try:
        connected = mongodb.is_connected()
        
        if not connected:
            connected = mongodb.connect()
        
        if connected:
            db_info = mongodb.get_database_info()
            return {
                "status": "healthy",
                "connected": True,
                "database": db_info.get("database_name", "unknown"),
                "collections": len(db_info.get("collections", [])),
                "message": "MongoDB is connected and accessible"
            }
        else:
            return {
                "status": "unhealthy", 
                "connected": False,
                "error": "Unable to connect to MongoDB"
            }
            
    except Exception as e:
        return {
            "status": "unhealthy",
            "connected": False, 
            "error": str(e)
        }


@router.get("/analysis")
async def list_all_analyses():
    """
    List all cached analyses with their status
    
    **Purpose:**
    - View all cached analyses in the database
    - Check cache statistics
    - Monitor expired entries
    
    **Returns:**
    - List of all analyses with cache info
    - Cache statistics (total, valid, expired)
    - Pagination info if many entries
    """
    try:
        # Get cache service
        cache_service = get_cache_service()
        
        if cache_service.collection is None:
            raise HTTPException(status_code=500, detail="Cache service not available")
        
        # Get cache statistics
        stats = cache_service.get_cache_stats()
        
        # Get all analyses (limit to 100 for performance)
        cursor = cache_service.collection.find({}).limit(100)
        analyses = []
        
        for doc in cursor:
            # Remove MongoDB ObjectId for JSON serialization
            doc.pop("_id", None)
            
            # Get cache info for this URL
            cache_info = cache_service.get_cache_info(doc.get("url", ""))
            
            # Include the full analysis object with metadata
            analysis_entry = {
                "url": doc.get("url"),
                "analysis_id": doc.get("analysis_id"),
                "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
                "expires_at": doc.get("expires_at").isoformat() if doc.get("expires_at") else None,
                "analysis_method": doc.get("analysis_method"),
                "expired": cache_info.get("expired", False),
                "has_error": bool(doc.get("error")),
                # Include the complete analysis data
                "terms_urls": doc.get("terms_urls", []),
                "analysis": doc.get("analysis"),
                "raw_analysis": doc.get("raw_analysis"),
                "error": doc.get("error")
            }
            
            analyses.append(analysis_entry)
        
        return {
            "cache_stats": stats,
            "analyses": analyses,
            "total_returned": len(analyses),
            "note": "Limited to 100 entries for performance" if len(analyses) == 100 else None
        }
        
    except Exception as e:
        logger.error(f"Error listing analyses: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/analysis/{url:path}")
async def get_specific_analysis(url: str):
    """
    Get cached analysis for a specific URL
    
    **Purpose:**
    - Check if analysis exists in cache
    - View cached analysis details
    - Check expiration status
    
    **Returns:**
    - Cached analysis if found
    - Cache information (created_at, expires_at, analysis_id)
    - 404 if not found
    
    - **url**: Website URL to look up (will be normalized)
    """
    try:
        # Normalize the URL for consistent lookup
        normalized_url = normalize_url(url)
        
        # Get cache service
        cache_service = get_cache_service()
        
        # Get cache info first
        cache_info = cache_service.get_cache_info(normalized_url)
        
        if not cache_info.get("cached"):
            raise HTTPException(
                status_code=404, 
                detail=f"No analysis found for URL: {normalized_url}"
            )
        
        # Get the actual analysis (even if expired)
        cached_analysis = cache_service.get_cached_analysis(normalized_url)
        
        return {
            "url": normalized_url,
            "cache_info": cache_info,
            "analysis": cached_analysis,
            "note": "Analysis may be expired but still retrievable" if cache_info.get("expired") else "Analysis is current"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis for {url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/analysis/{url:path}")
async def delete_analysis(url: str):
    """
    Delete cached analysis for a specific URL
    
    **Purpose:**
    - Remove analysis from cache
    - Force fresh analysis on next request
    - Clean up expired or incorrect data
    
    **Returns:**
    - Success message if deleted
    - 404 if not found
    
    - **url**: Website URL to delete from cache (will be normalized)
    """
    try:
        # Normalize the URL for consistent lookup
        normalized_url = normalize_url(url)
        
        # Get cache service and collection
        cache_service = get_cache_service()
        
        if cache_service.collection is None:
            raise HTTPException(status_code=500, detail="Cache service not available")
        
        # Check if analysis exists
        cache_info = cache_service.get_cache_info(normalized_url)
        if not cache_info.get("cached"):
            raise HTTPException(
                status_code=404, 
                detail=f"No analysis found for URL: {normalized_url}"
            )
        
        # Delete the analysis
        result = cache_service.collection.delete_one({"url": normalized_url})
        
        if result.deleted_count > 0:
            logger.info(f"🗑️ Deleted analysis for: {normalized_url}")
            return {
                "message": "Analysis deleted successfully",
                "url": normalized_url,
                "analysis_id": cache_info.get("analysis_id"),
                "deleted_count": result.deleted_count
            }
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"Failed to delete analysis for URL: {normalized_url}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting analysis for {url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/analysis")
async def clear_expired_analyses():
    """
    Clear all expired cached analyses
    
    **Purpose:**
    - Clean up expired cache entries
    - Free up database space
    - Maintain cache hygiene
    
    **Returns:**
    - Number of entries removed
    - Updated cache statistics
    """
    try:
        # Get cache service
        cache_service = get_cache_service()
        
        # Clear expired entries
        deleted_count = cache_service.clear_expired_cache()
        
        # Get updated stats
        stats = cache_service.get_cache_stats()
        
        logger.info(f"🧹 Cleared {deleted_count} expired cache entries")
        
        return {
            "message": f"Cleared {deleted_count} expired analyses",
            "deleted_count": deleted_count,
            "updated_stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error clearing expired analyses: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


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
    Analyze Terms & Conditions using AI with intelligent caching
    
    **Caching Strategy:**
    1. Check if analysis exists in cache for this URL
    2. If cached and not expired (within 3 months) → return cached result
    3. If cached but expired → re-analyze with AI and update cache
    4. If not cached → analyze with AI and store result
    
    **Process Flow:**
    1. Check cache first (saves AI API costs)
    2. Find Terms & Conditions URLs (no AI cost)
    3. Only if terms found → call AI for analysis
    4. Store result in cache for future requests
    5. Return detailed privacy assessment with data buyers list
    
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
        
        # Get cache service
        cache_service = get_cache_service()
        
        # Check if we have a cached analysis that's still valid
        cached_analysis = cache_service.get_cached_analysis(normalized_url)
        if cached_analysis:
            logger.info(f"📋 Returning cached analysis for: {normalized_url}")
            return cached_analysis
        
        # Check cache info to see if we had an expired entry
        cache_info = cache_service.get_cache_info(normalized_url)
        if cache_info.get("cached") and cache_info.get("expired"):
            logger.info(f"♻️ Cached analysis expired for: {normalized_url}, re-analyzing...")
        else:
            logger.info(f"🆕 No cached analysis found for: {normalized_url}, analyzing...")
        
        # Proceed with fresh analysis...
        
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
        
        # Create the response object
        response = AIAnalysisResponse(
            url=normalized_url,  # Use normalized URL for consistency
            terms_urls=terms_result.found_terms_pages,
            analysis=structured_analysis,
            raw_analysis=raw_analysis,  # Only present when structured parsing fails
            analysis_method=analysis_method,
            error=None if analysis else "AI analysis failed"
        )
        
        # Save to cache if analysis was successful
        if analysis:
            saved = cache_service.save_analysis(response)
            if saved:
                logger.info(f"💾 Saved analysis to cache for: {normalized_url}")
            else:
                logger.warning(f"⚠️ Failed to save analysis to cache for: {normalized_url}")
        
        return response
        
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
