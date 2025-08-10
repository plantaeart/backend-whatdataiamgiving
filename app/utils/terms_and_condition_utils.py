"""
Terms and Conditions utilities for web scraping
"""

import asyncio
import logging
import random
from typing import List
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from app.config import settings
from app.models.terms_response import TermsResponse
from app.models.terms_check_response import TermsCheckResponse

logger = logging.getLogger(__name__)


class TermsAndConditionUtils:
    """Utility class for finding Terms & Conditions pages"""
    
    @staticmethod
    def _get_friendly_error_message(url: str, status_code: int | None = None, error_type: str = "http") -> str:
        """
        Generate user-friendly error messages for common scraping issues
        
        Args:
            url: The URL that failed
            status_code: HTTP status code (if applicable)
            error_type: Type of error ("http", "timeout", "connection", "generic")
        """
        domain = urlparse(url).netloc.lower()
        
        # Generate appropriate message based on error type and status code
        if error_type == "http" and status_code:
            if status_code == 403:
                return f"🛡️ Access denied by {domain}. The website blocks automated requests."
            
            elif status_code == 404:
                return f"🔍 Page not found on {domain}. The URL may have changed or been removed."
            
            elif status_code == 429:
                return f"⏰ Rate limited by {domain}. Too many requests - please try again later."
            
            elif status_code == 503:
                return f"🔧 Service unavailable on {domain}. The website may be under maintenance."
            
            elif status_code in [500, 502, 504]:
                return f"🖥️ Server error on {domain} (HTTP {status_code}). The website is experiencing technical issues."
            
            elif 400 <= status_code < 500:
                return f"⚠️ Client error when accessing {domain} (HTTP {status_code}). The request was rejected."
            
            elif 500 <= status_code < 600:
                return f"🖥️ Server error on {domain} (HTTP {status_code}). The website has internal issues."
            
            else:
                return f"❌ HTTP error {status_code} when accessing {domain}."
        
        elif error_type == "timeout":
            return f"⏱️ Request timeout for {domain}. The server took too long to respond."
        
        elif error_type == "connection":
            return f"🔌 Connection failed to {domain}. Check your internet connection or try again later."
        
        elif error_type == "ssl":
            return f"🔒 SSL/TLS error when connecting to {domain}. The website has certificate issues."
        
        else:
            return f"❌ Unable to access {domain}. The website may be temporarily unavailable."
    
    async def _make_request_with_retry(self, url: str, retries: int = 2) -> tuple[str, str, str | None]:
        """
        Make HTTP request with retry logic and random delays to avoid rate limiting
        Returns: (final_url, html_content, error_message)
        """
        for attempt in range(retries + 1):
            try:
                # Add random delay between requests to be respectful
                if attempt > 0:
                    delay = random.uniform(1, 3)
                    logger.info(f"⏳ Retry {attempt}/{retries} for {url} after {delay:.1f}s delay")
                    await asyncio.sleep(delay)
                
                async with httpx.AsyncClient(
                    timeout=settings.REQUEST_TIMEOUT,
                    headers=settings.DEFAULT_HEADERS,
                    follow_redirects=True
                ) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    return str(response.url), response.text, None
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    friendly_msg = self._get_friendly_error_message(url, 403, "http")
                    logger.warning(f"🚫 {friendly_msg}")
                    if attempt == retries:
                        # On final attempt, return error message
                        return "", "", friendly_msg
                elif e.response.status_code == 429:
                    friendly_msg = self._get_friendly_error_message(url, 429, "http")
                    logger.warning(f"⏰ {friendly_msg}")
                    if attempt < retries:
                        continue
                    else:
                        return "", "", friendly_msg
                else:
                    friendly_msg = self._get_friendly_error_message(url, e.response.status_code, "http")
                    logger.error(f"❌ {friendly_msg}")
                    return "", "", friendly_msg
            except httpx.TimeoutException:
                friendly_msg = self._get_friendly_error_message(url, None, "timeout")
                logger.warning(f"⏱️ {friendly_msg}")
                if attempt < retries:
                    continue
                return "", "", friendly_msg
            except httpx.ConnectError:
                friendly_msg = self._get_friendly_error_message(url, None, "connection")
                logger.error(f"🔌 {friendly_msg}")
                return "", "", friendly_msg
            except Exception as e:
                if "ssl" in str(e).lower() or "certificate" in str(e).lower():
                    friendly_msg = self._get_friendly_error_message(url, None, "ssl")
                    logger.error(f"🔒 {friendly_msg}")
                else:
                    friendly_msg = self._get_friendly_error_message(url, None, "generic")
                    logger.error(f"❌ {friendly_msg}")
                    
                return "", "", friendly_msg
        
        # If we get here, all retries failed
        generic_msg = self._get_friendly_error_message(url, None, "generic")
        return "", "", generic_msg

    async def find_terms_links(self, base_url: str, html_content: str) -> List[str]:
        """Find the most relevant Terms & Conditions links from HTML content"""
        found_links = []  # Will store (url, link_text) tuples
        internal_links = []
        external_links = []
        
        # Parse base domain for comparison
        base_domain = urlparse(base_url).netloc.lower()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all links in the page
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            # Ensure it's a Tag element, not NavigableString
            if not isinstance(link, Tag):
                continue
                
            href = link.get('href')
            if not href or not isinstance(href, str):
                continue
                
            link_text = link.get_text(strip=True)
            
            # Convert relative URLs to absolute
            full_url = urljoin(base_url, href)
            
            # Skip invalid URLs
            if not full_url.startswith(('http://', 'https://')):
                continue
                
            # Check if this link might be a terms/privacy link
            terms_patterns = [
                'terms', 'condition', 'privacy', 'policy', 'legal',
                'agreement', 'données', 'confidentialité', 'mentions',
                'cookies', 'politique', 'cgv', 'cgu'
            ]
            
            link_text_lower = link_text.lower()
            href_lower = href.lower()
            
            is_terms_link = any(pattern in link_text_lower for pattern in terms_patterns) or \
                           any(pattern in href_lower for pattern in terms_patterns)
            
            if is_terms_link:
                # Determine if it's internal or external
                link_domain = urlparse(full_url).netloc.lower()
                link_data = (full_url, link_text)
                
                if link_domain == base_domain:
                    internal_links.append(link_data)
                else:
                    external_links.append(link_data)
        
        # Process internal links first (priority), then external if needed
        all_candidate_links = internal_links + external_links
        
        # Follow links to get final URLs
        final_links = []
        for potential_url, link_text in all_candidate_links:
            final_url = await self._follow_terms_link(potential_url)
            if final_url:
                final_links.append((final_url, link_text))
        
        # If no links found, try common URL patterns as fallback
        if not final_links:
            logger.info(f"🔄 No terms links found on page, trying common URL patterns...")
            fallback_urls = await self._try_common_terms_urls(base_url)
            final_links.extend(fallback_urls)
        
        # Select the most relevant URL using scoring system (returns only the best one)
        most_relevant = self._select_most_relevant_urls(final_links)
        
        return most_relevant
    
    async def _follow_terms_link(self, link_url: str) -> str:
        """
        Follow a terms link to get the final URL after all redirects
        Uses retry logic and browser-like headers to avoid bot detection
        Returns: final_url
        """
        try:
            final_url, _, _ = await self._make_request_with_retry(link_url)
            return final_url if final_url else link_url  # Return original if request failed
        except Exception as e:
            logger.error(f"❌ Error following link {link_url}: {str(e)}")
            return link_url  # Return original URL as fallback

    @staticmethod
    def _calculate_relevance_score(url: str, link_text: str) -> int:
        """
        Calculate relevance score for a potential terms link
        Higher score = more relevant
        """
        score = 0
        url_lower = url.lower()
        text_lower = link_text.lower()
        
        # High priority patterns (exact matches)
        high_priority = [
            'terms of service', 'terms and conditions', 'terms & conditions',
            'privacy policy', 'privacy notice', 'data policy',
            'cookie policy', 'cookies policy'
        ]
        
        # Medium priority patterns
        medium_priority = [
            'terms', 'conditions', 'privacy', 'legal', 'policy',
            'agreement', 'cookies', 'data protection'
        ]
        
        # French equivalents
        french_high = [
            'conditions générales', 'conditions d\'utilisation', 'mentions légales',
            'politique de confidentialité', 'politique des données',
            'politique des cookies', 'gestion des cookies'
        ]
        
        french_medium = [
            'conditions', 'confidentialité', 'données', 'cookies',
            'mentions', 'légales', 'politique', 'cgv', 'cgu'
        ]
        
        # Check high priority patterns
        for pattern in high_priority + french_high:
            if pattern in text_lower:
                score += 100
            if pattern in url_lower:
                score += 80
        
        # Check medium priority patterns
        for pattern in medium_priority + french_medium:
            if pattern in text_lower:
                score += 50
            if pattern in url_lower:
                score += 30
        
        # Bonus points for URL structure indicators
        if '/terms' in url_lower or '/privacy' in url_lower:
            score += 40
        if '/legal' in url_lower or '/policy' in url_lower:
            score += 30
        if '/cookies' in url_lower:
            score += 25
        
        # Penalty for generic or irrelevant links
        penalty_patterns = [
            'contact', 'about', 'help', 'support', 'news', 'blog',
            'careers', 'jobs', 'press', 'media', 'investor'
        ]
        
        for pattern in penalty_patterns:
            if pattern in text_lower or pattern in url_lower:
                score -= 20
        
        # Bonus for being in footer or legal sections
        if any(indicator in text_lower for indicator in ['footer', 'legal', 'bottom']):
            score += 10
        
        return max(0, score)  # Ensure non-negative score

    def _select_most_relevant_urls(self, found_urls: List[tuple], max_results: int = 1) -> List[str]:
        """
        Select the most relevant URL from found links (returns only the highest scoring one)
        
        Args:
            found_urls: List of (url, link_text) tuples
            max_results: Not used - always returns only the best match
            
        Returns:
            List containing only the highest scoring URL (or empty if no valid URLs)
        """
        if not found_urls:
            return []
        
        # Calculate scores for all URLs
        scored_urls = []
        for url, link_text in found_urls:
            score = self._calculate_relevance_score(url, link_text)
            if score > 0:  # Only consider URLs with positive scores
                scored_urls.append((score, url, link_text))
        
        if not scored_urls:
            logger.info("🚫 No URLs with positive relevance scores found")
            return []
        
        # Sort by score (highest first) and get the best one
        scored_urls.sort(key=lambda x: x[0], reverse=True)
        
        # Get the highest scoring URL
        best_score, best_url, best_text = scored_urls[0]
        
        logger.info(f"🏆 Selected BEST URL (score: {best_score}): {best_url} - '{best_text[:50]}...'")
        
        if len(scored_urls) > 1:
            logger.info(f"🎯 Chose 1 best URL from {len(scored_urls)} candidates")
            # Log the top 3 candidates for debugging
            for i, (score, url, text) in enumerate(scored_urls[:3]):
                status = "🏆 SELECTED" if i == 0 else f"#{i+1}"
                logger.info(f"   {status} (score: {score}): {text[:30]}...")
        
        return [best_url]

    async def _try_common_terms_urls(self, base_url: str) -> List[tuple]:
        """
        Fallback method to try common URL patterns for terms & conditions
        Used when no links are found on the main page (e.g., SPA sites)
        """
        from urllib.parse import urljoin
        
        # Common URL patterns for terms & conditions pages
        common_patterns = [
            # English patterns
            '/terms', '/terms-of-service', '/terms-and-conditions', '/tos',
            '/privacy', '/privacy-policy', '/privacy-notice',
            '/legal', '/legal-notice', '/legal-information',
            '/cookies', '/cookie-policy', '/cookie-notice',
            
            # French patterns  
            '/mentions-legales', '/politique-confidentialite', '/politique-cookies',
            '/conditions-generales', '/conditions-utilisation', '/cgv', '/cgu',
            '/politique-donnees', '/confidentialite', '/donnees-personnelles',
            
            # Common subdirectory patterns
            '/legal/terms', '/legal/privacy', '/legal/cookies',
            '/accueil/politique-cookies', '/accueil/mentions-legales',
            '/fr/legal', '/fr/privacy', '/fr/mentions-legales'
        ]
        
        found_urls = []
        base_domain = urlparse(base_url).netloc.lower()
        
        for pattern in common_patterns:
            test_url = urljoin(base_url, pattern)
            
            try:
                # Use simple HTTP check instead of _make_request_with_retry to avoid complex retry logic
                async with httpx.AsyncClient(
                    headers=settings.DEFAULT_HEADERS,
                    timeout=5.0,  # Shorter timeout for fallback checks
                    follow_redirects=True
                ) as client:
                    response = await client.get(test_url)
                    
                    if response.status_code == 200:
                        # Create a descriptive text based on the pattern
                        if 'privacy' in pattern or 'confidentialite' in pattern:
                            link_text = "Privacy Policy"
                        elif 'cookie' in pattern:
                            link_text = "Cookie Policy" 
                        elif 'mention' in pattern:
                            link_text = "Mentions Légales"
                        elif 'terms' in pattern or 'condition' in pattern:
                            link_text = "Terms & Conditions"
                        else:
                            link_text = "Legal Information"
                        
                        found_urls.append((str(response.url), link_text))
                        logger.info(f"✅ Found fallback URL: {response.url} ({link_text})")
                        
            except Exception as e:
                # Silently continue - most URLs won't exist
                pass
        
        if found_urls:
            logger.info(f"🎯 Fallback found {len(found_urls)} potential terms URLs")
        else:
            logger.info("❌ No fallback URLs found")
            
        return found_urls

    async def check_terms_exist(self, url: str) -> TermsCheckResponse:
        """Check if a website has Terms & Conditions pages"""
        try:
            logger.info(f"🔍 Checking for terms on: {url}")
            
            final_url, html_content, error_msg = await self._make_request_with_retry(url)
            
            if not html_content:
                # Use the specific error message from the request if available
                if error_msg:
                    logger.warning(f"⚠️ {error_msg}")
                    return TermsCheckResponse(
                        url=url,
                        has_terms=False,
                        found_terms_pages=[],
                        error=error_msg
                    )
                else:
                    # Fallback to generic error if no specific error provided
                    generic_error = self._get_friendly_error_message(url, None, "generic")
                    logger.warning(f"⚠️ {generic_error}")
                    return TermsCheckResponse(
                        url=url,
                        has_terms=False,
                        found_terms_pages=[],
                        error=generic_error
                    )
            
            # Find potential terms links
            terms_links = await self.find_terms_links(url, html_content)
            
            return TermsCheckResponse(
                url=url,
                has_terms=len(terms_links) > 0,
                found_terms_pages=terms_links
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
        """Find Terms & Conditions pages from a website URL"""
        try:
            logger.info(f"🔍 Searching for terms pages on: {url}")
            
            final_url, html_content, error_msg = await self._make_request_with_retry(url)
            
            if not html_content:
                # Use the specific error message from the request if available, otherwise generic
                if not error_msg:
                    error_msg = self._get_friendly_error_message(url, None, "generic")
                return TermsResponse(
                    url=url,
                    has_terms=False,
                    found_terms_pages=[],
                    error=error_msg
                )
            
            # Find potential terms links
            terms_links = await self.find_terms_links(url, html_content)
            
            return TermsResponse(
                url=url,
                has_terms=len(terms_links) > 0,
                found_terms_pages=terms_links
            )
            
        except Exception as e:
            error_msg = f"Error searching {url}: {str(e)}"
            logger.error(error_msg)
            return TermsResponse(
                url=url,
                has_terms=False,
                found_terms_pages=[],
                error=error_msg
            )
