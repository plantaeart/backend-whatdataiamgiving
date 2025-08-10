"""
Models package for WhatDataIAmGiving API
"""

from .terms_request import TermsRequest
from .terms_response import TermsResponse
from .terms_check_response import TermsCheckResponse

__all__ = [
    "TermsRequest",
    "TermsResponse", 
    "TermsCheckResponse"
]
