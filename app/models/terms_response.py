"""
TermsResponse model for API responses
"""

from typing import List, Optional
from pydantic import BaseModel

class TermsResponse(BaseModel):
    url: str
    has_terms: bool
    found_terms_pages: List[str]
    error: Optional[str] = None
