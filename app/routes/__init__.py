"""
Routes package for WhatDataIAmGiving API
"""

from .term_and_condition import router as terms_router

__all__ = [
    "terms_router"
]
