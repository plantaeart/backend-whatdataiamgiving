"""
TermsCheckResponse model for terms existence checking
"""

from typing import List, Optional
from pydantic import BaseModel


class TermsCheckResponse(BaseModel):
    url: str
    has_terms: bool
    found_terms_pages: List[str]
    error: Optional[str] = None
