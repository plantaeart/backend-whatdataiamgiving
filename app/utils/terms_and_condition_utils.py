"""
Terms and Conditions utility functions for web scraping
"""

from typing import List
import re
from urllib.parse import urljoin
import logging

import httpx
from bs4 import BeautifulSoup

from ..models import TermsResponse, TermsCheckResponse
from ..config import settings

logger = logging.getLogger(__name__)


class TermsAndConditionUtils:
    """Utility class for scraping Terms & Conditions from websites"""
    
    def __init__(self):
        self.common_terms_patterns = settings.TERMS_PATTERNS
        
    async def find_terms_links(self, base_url: str, html_content: str) -> List[str]:
        """Find potential Terms & Conditions links on a webpage"""
        terms_links = []
        
        # Use regex to find href attributes in anchor tags
        href_pattern = r'<a[^>]*href\s*=\s*["\']([^"\']*)["\'][^>]*>([^<]*)</a>'
        matches = re.findall(href_pattern, html_content, re.IGNORECASE)
        
        for href, link_text in matches:
            try:
                text = link_text.strip().lower()
                href_str = str(href)
                
                # Check if link text or href contains terms-related keywords
                for pattern in self.common_terms_patterns:
                    if re.search(pattern, text, re.IGNORECASE) or re.search(pattern, href_str, re.IGNORECASE):
                        full_url = urljoin(base_url, href_str)
                        if full_url not in terms_links:
                            terms_links.append(full_url)
                            break  # Found match, no need to check other patterns
            except Exception:
                # Skip problematic links
                continue
                        
        return terms_links
    
    async def scrape_terms_content(self, url: str) -> str:
        """Scrape Terms & Conditions content from a single URL"""
        try:
            async with httpx.AsyncClient(
                timeout=settings.REQUEST_TIMEOUT,
                headers={'User-Agent': settings.USER_AGENT}
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "header", "footer"]):
                    script.decompose()
                
                # Try to find main content areas
                content_selectors = [
                    'main', 'article', '.content', '#content', 
                    '.terms', '.privacy', '.legal-text',
                    '.policy-content', '[role="main"]'
                ]
                
                content_text = ""
                for selector in content_selectors:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        content_text = content_elem.get_text(separator=' ', strip=True)
                        break
                
                # Fallback to body text if no specific content found
                if not content_text:
                    content_text = soup.body.get_text(separator=' ', strip=True) if soup.body else ""
                
                # Clean up the text
                content_text = re.sub(r'\s+', ' ', content_text)  # Normalize whitespace
                content_text = re.sub(r'\n+', '\n', content_text)  # Normalize newlines
                
                return content_text.strip()
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return ""
    
    async def check_terms_exist(self, url: str) -> TermsCheckResponse:
        """Check if a website has Terms & Conditions pages"""
        try:
            logger.info(f"Checking for terms on: {url}")
            
            async with httpx.AsyncClient(
                timeout=settings.REQUEST_TIMEOUT,
                headers={'User-Agent': settings.USER_AGENT}
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                html_content = response.text
            
            # Find potential terms links
            terms_links = await self.find_terms_links(url, html_content)
            
            return TermsCheckResponse(
                url=url,
                has_terms=len(terms_links) > 0,
                found_terms_pages=terms_links
            )
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code} when accessing {url}"
            logger.error(error_msg)
            return TermsCheckResponse(
                url=url,
                has_terms=False,
                found_terms_pages=[],
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Error checking {url}: {str(e)}"
            logger.error(error_msg)
            return TermsCheckResponse(
                url=url,
                has_terms=False,
                found_terms_pages=[],
                error=error_msg
            )
    
    async def scrape_website_terms(self, url: str) -> TermsResponse:
        """Main method to scrape Terms & Conditions from a website"""
        try:
            logger.info(f"Starting scrape for: {url}")
            
            # First, get the main page to find terms links
            async with httpx.AsyncClient(
                timeout=settings.REQUEST_TIMEOUT,
                headers={'User-Agent': settings.USER_AGENT}
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                main_page_html = response.text
            
            # Find potential terms links
            terms_links = await self.find_terms_links(url, main_page_html)
            
            # If no specific terms links found, try the main page
            if not terms_links:
                terms_links = [url]
            
            # Limit to configured max pages to avoid overwhelming
            terms_links = terms_links[:settings.MAX_TERMS_PAGES]
            
            # Scrape content from all found terms pages
            all_terms_text = ""
            scraped_urls = []
            
            for terms_url in terms_links:
                content = await self.scrape_terms_content(terms_url)
                if content and len(content) > settings.MIN_CONTENT_LENGTH:  # Only include substantial content
                    all_terms_text += f"\n\n--- Content from {terms_url} ---\n{content}"
                    scraped_urls.append(terms_url)
            
            return TermsResponse(
                url=url,
                found_terms_pages=scraped_urls,
                extracted_text=all_terms_text,
                text_length=len(all_terms_text)
            )
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code} when accessing {url}"
            logger.error(error_msg)
            return TermsResponse(
                url=url,
                found_terms_pages=[],
                extracted_text="",
                text_length=0,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Error scraping {url}: {str(e)}"
            logger.error(error_msg)
            return TermsResponse(
                url=url,
                found_terms_pages=[],
                extracted_text="",
                text_length=0,
                error=error_msg
            )
