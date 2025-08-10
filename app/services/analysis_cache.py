"""
Website Analysis Cache Service
Manages storing and retrieving cached analysis results from MongoDB.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

from app.database import get_analysis_collection
from app.models.website_analysis import WebsiteAnalysisDocument, WebsiteAnalysisRequest
from app.models.ai_analysis_response import AIAnalysisResponse

logger = logging.getLogger(__name__)


class WebsiteAnalysisCacheService:
    """Service for managing website analysis cache in MongoDB."""
    
    def __init__(self):
        # Don't get collection during init - get it dynamically when needed
        self._collection = None
    
    @property
    def collection(self):
        """Get the collection, refreshing if needed."""
        # Always get fresh collection reference to handle reconnections
        return get_analysis_collection()
    
    def get_cached_analysis(self, url: str) -> Optional[AIAnalysisResponse]:
        """
        Get cached analysis for a URL if it exists and hasn't expired.
        
        Args:
            url: The URL to check for cached analysis
            
        Returns:
            AIAnalysisResponse if found and valid, None otherwise
        """
        if self.collection is None:
            logger.error("Analysis collection not available")
            return None
        
        try:
            # Find analysis by URL that hasn't expired
            query = {
                "url": url,
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            }
            
            document = self.collection.find_one(query)
            
            if document:
                logger.info(f"Found cached analysis for URL: {url}")
                
                # Convert MongoDB document back to AIAnalysisResponse
                # Remove MongoDB-specific fields
                document.pop("_id", None)
                document.pop("analysis_id", None)
                document.pop("created_at", None)
                document.pop("expires_at", None)
                
                return AIAnalysisResponse(**document)
            
            logger.info(f"No cached analysis found for URL: {url}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached analysis for {url}: {e}")
            return None
    
    def save_analysis(self, analysis: AIAnalysisResponse) -> bool:
        """
        Save analysis result to cache.
        
        Args:
            analysis: The AIAnalysisResponse to cache
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        if self.collection is None:
            logger.error("Analysis collection not available")
            return False
        
        try:
            # Get the next sequential analysis_id
            max_id_doc = self.collection.find_one(
                {},
                sort=[("analysis_id", -1)]
            )
            next_analysis_id = 1 if not max_id_doc else max_id_doc.get("analysis_id", 0) + 1
            
            # Create MongoDB document from AIAnalysisResponse
            document = WebsiteAnalysisDocument(
                **analysis.model_dump(),
                analysis_id=next_analysis_id,
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=90)  # 3 months cache
            )
            
            # Use upsert to replace existing analysis for the same URL
            result = self.collection.replace_one(
                {"url": analysis.url},
                document.to_dict(),
                upsert=True
            )
            
            if result.acknowledged:
                action = "updated" if result.matched_count > 0 else "inserted"
                logger.info(f"Successfully {action} analysis cache for URL: {analysis.url}")
                return True
            else:
                logger.error(f"Failed to save analysis cache for URL: {analysis.url}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving analysis cache for {analysis.url}: {e}")
            return False
    
    def is_analysis_cached(self, url: str) -> bool:
        """
        Check if analysis is cached and valid for a URL.
        
        Args:
            url: The URL to check
            
        Returns:
            bool: True if cached and valid, False otherwise
        """
        return self.get_cached_analysis(url) is not None
    
    def get_cache_info(self, url: str) -> dict:
        """
        Get cache information for a URL.
        
        Args:
            url: The URL to check
            
        Returns:
            dict: Cache information
        """
        if self.collection is None:
            return {"cached": False, "error": "Collection not available"}
        
        try:
            document = self.collection.find_one({"url": url})
            
            if not document:
                return {"cached": False}
            
            expires_at = document.get("expires_at")
            created_at = document.get("created_at")
            now = datetime.now(timezone.utc)
            
            # Ensure expires_at is timezone-aware for comparison
            is_expired = False
            if expires_at:
                if expires_at.tzinfo is None:
                    # If expires_at is timezone-naive, assume it's UTC
                    expires_at_utc = expires_at.replace(tzinfo=timezone.utc)
                else:
                    expires_at_utc = expires_at
                is_expired = expires_at_utc < now
            
            return {
                "cached": True,
                "expired": is_expired,
                "created_at": created_at.isoformat() if created_at else None,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "analysis_id": document.get("analysis_id")
            }
            
        except Exception as e:
            logger.error(f"Error getting cache info for {url}: {e}")
            return {"cached": False, "error": str(e)}
    
    def clear_expired_cache(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            int: Number of entries removed
        """
        if self.collection is None:
            logger.error("Analysis collection not available")
            return 0
        
        try:
            result = self.collection.delete_many({
                "expires_at": {"$lt": datetime.now(timezone.utc)}
            })
            
            count = result.deleted_count
            if count > 0:
                logger.info(f"Removed {count} expired cache entries")
            
            return count
            
        except Exception as e:
            logger.error(f"Error clearing expired cache: {e}")
            return 0
    
    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            dict: Cache statistics
        """
        if self.collection is None:
            return {"error": "Collection not available"}
        
        try:
            now = datetime.now(timezone.utc)
            
            total_count = self.collection.count_documents({})
            valid_count = self.collection.count_documents({
                "expires_at": {"$gt": now}
            })
            expired_count = total_count - valid_count
            
            return {
                "total_entries": total_count,
                "valid_entries": valid_count,
                "expired_entries": expired_count,
                "cache_hit_rate": None  # Could be calculated with request tracking
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}


# Global cache service instance
cache_service = WebsiteAnalysisCacheService()


def get_cache_service() -> WebsiteAnalysisCacheService:
    """Get the global cache service instance."""
    return cache_service
