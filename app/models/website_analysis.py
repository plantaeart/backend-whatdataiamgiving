"""
Database Models for MongoDB Collections - Website Analysis
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel, Field

from app.models.ai_analysis_response import AIAnalysisResponse


class WebsiteAnalysisDocument(AIAnalysisResponse):
    """MongoDB document model for website analysis - extends AIAnalysisResponse."""
    
    # MongoDB document ID (string representation)
    id: Optional[str] = Field(None, alias="_id", description="MongoDB document ID")
    
    # Additional MongoDB-specific fields
    analysis_id: int = Field(..., description="Unique sequential analysis identifier")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        description="When this analysis was created"
    )
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=90), 
        description="When this analysis expires (3 months cache)"
    )
    
    class Config:
        validate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z" if v.tzinfo else v.isoformat()
        }
        
    def to_dict(self):
        """Convert to dictionary for MongoDB insertion."""
        return self.model_dump(by_alias=True, exclude_unset=True)


class WebsiteAnalysisRequest(BaseModel):
    """Request model for website analysis."""
    
    url: str = Field(..., description="URL to analyze")
    force_refresh: bool = Field(False, description="Force new analysis even if cached version exists")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/terms",
                "force_refresh": False
            }
        }
