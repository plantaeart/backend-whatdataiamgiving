"""
TermsResponse model for API responses
"""

from typing import List, Optional
from pydantic import BaseModel


class TermsResponse(BaseModel):
    url: str
    found_terms_pages: List[str]
    extracted_text: str
    text_length: int
    error: Optional[str] = None
