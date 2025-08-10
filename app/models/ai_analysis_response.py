"""
AI Analysis response models
"""

from typing import Optional, List, Dict
from pydantic import BaseModel, field_validator


class TermsAnalysis(BaseModel):
    ok: List[str]
    neutral: List[str]
    bad: List[str]


class DetailedAIAnalysis(BaseModel):
    privacy_score: int  # 0-100
    score_explanation: str
    terms_analysis: TermsAnalysis
    data_selling: str
    data_buyers: List[str]  # List of companies/types that buy data
    data_storage: str
    main_concerns: List[str]
    user_rights: str
    summary: str


class AIAnalysisResponse(BaseModel):
    url: str
    terms_urls: List[str]
    analysis: Optional[DetailedAIAnalysis] = None
    raw_analysis: Optional[dict] = None  # Fallback for non-structured responses
    analysis_method: str  # "url" or "text" or "failed"
    error: Optional[str] = None


class AnalyzeTermsRequest(BaseModel):
    url: str
    
    @field_validator('url')
    def validate_url(cls, v):
        """Ensure URL is a non-empty string"""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")
        return v.strip()
