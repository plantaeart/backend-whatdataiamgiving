"""
TermsRequest model for API requests
"""

from pydantic import BaseModel, HttpUrl, field_validator


class TermsRequest(BaseModel):
    url: HttpUrl
    
    @field_validator('url')
    def validate_url(cls, v):
        """Ensure URL is valid"""
        return str(v)
