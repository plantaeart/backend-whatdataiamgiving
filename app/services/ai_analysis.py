"""
AI service for analyzing Terms & Conditions
"""

import logging
from typing import Dict, Any, Optional

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.config import settings

logger = logging.getLogger(__name__)


class AIAnalysisService:
    """Service for analyzing Terms & Conditions using Google Gemini"""
    
    def __init__(self):
        self.model = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of the Gemini model"""
        if not self._initialized:
            from app.config import settings
            if settings.GEMINI_API_KEY:
                try:
                    genai.configure(api_key=settings.GEMINI_API_KEY)
                    self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
                    logger.info(f"AI Service: Gemini model initialized successfully with {settings.GEMINI_MODEL}")
                    self._initialized = True
                except Exception as e:
                    logger.error(f"AI Service: Failed to initialize Gemini model: {e}")
                    self.model = None
                    self._initialized = True  # Mark as attempted to avoid repeated failures
            else:
                logger.warning("AI Service: GEMINI_API_KEY not set. AI analysis will be disabled.")
                self.model = None
                self._initialized = True
    
    def _get_analysis_prompt(self) -> str:
        """Get the prompt for terms & conditions analysis"""
        return """
You are an expert in privacy law and data protection. Analyze the Terms & Conditions or Privacy Policy and provide a detailed privacy assessment.

**CRITICAL SCORING RULES:**
- If data is sold or shared with third parties for ANY commercial purpose: MAX score is 35
- If data is shared for advertising, marketing, or analytics with external companies: MAX score is 40
- If data retention is indefinite, unclear, or longer than 2 years: Reduce score by 20-30 points
- If data is kept longer than necessary for stated purposes: Reduce score by 15-25 points
- If users cannot easily delete their data or opt-out: Reduce score by 20 points
- If no clear data deletion timeline is provided: Reduce score by 15 points

**ACCEPTABLE DATA PRACTICES (Higher scores possible):**
- Internal analytics only (no external sharing): Acceptable if data is anonymized
- Short retention periods (30 days - 1 year) with clear deletion policies: Good practice
- Easy user control over data deletion and export: Excellent practice
- Data used only for core service functionality: Best practice

Please provide:

1. **Privacy Score (0-100)**: Rate the overall privacy protection level
   - 90-100: Excellent privacy protection (no external sharing, short retention, strong user control)
   - 70-89: Good privacy protection (minimal sharing, reasonable retention, good user rights)
   - 50-69: Moderate privacy protection (some concerning practices, average user control)
   - 30-49: Poor privacy protection (third-party sharing, long retention, weak user rights)
   - 0-29: Very poor privacy protection (extensive sharing/selling, indefinite retention, no user control)

**AUTOMATIC SCORE REDUCTIONS:**
- Data selling or extensive third-party sharing: -40 to -65 points
- Sharing with advertising networks/marketing companies: -30 to -45 points
- Sharing with "business partners" or "affiliates": -25 to -35 points
- Indefinite or unclear data retention: -20 to -30 points
- Data kept longer than 2 years without justification: -15 to -25 points
- Poor user control/deletion options: -15 to -25 points
- No clear data deletion timeline: -10 to -20 points

2. **Categorized Terms Analysis**:
   - **OK (Good practices)**: Internal analytics, short retention, strong user control, data minimization
   - **NEUTRAL (Standard practices)**: Standard industry practices with clear limitations
   - **BAD (Concerning practices)**: External sharing, long retention, weak user control (ALWAYS include third-party sharing here)

3. **Key Areas**: Analyze these specific aspects:
   - Data collection and types
   - Data sharing with third parties (ANY external sharing is concerning)
   - Data retention periods and deletion policies
   - User rights and control (deletion, export, opt-out)
   - Cookie usage and tracking
   - Data selling practices
   - **Data buyers identification**: Any external companies receiving data
   - **Data retention details**: How long data is kept and when it's deleted

Format your response as JSON with these exact keys:
{
  "privacy_score": number (0-100),
  "score_explanation": "Brief explanation focusing on data sharing and retention impact on score",
  "terms_analysis": {
    "ok": ["list of positive practices - internal use, short retention, user control"],
    "neutral": ["list of standard practices with clear limitations"], 
    "bad": ["list of concerning practices - ALWAYS include external sharing and long retention"]
  },
  "data_selling": "Does the site sell user data or share with third parties? How?",
  "data_buyers": ["list of ALL external companies or types receiving data", "including analytics providers", "advertising networks", "business partners"],
  "data_storage": "How and where is data stored? Include retention periods and deletion policies.",
  "main_concerns": ["list of top 3 privacy concerns - prioritize sharing and retention issues"],
  "user_rights": "What rights do users have? Include data deletion and export rights.",
  "summary": "2-sentence overall summary emphasizing data sharing and retention practices"
}

**Important**: For data_buyers, include ALL external data recipients:
- ANY third-party analytics companies (even Google Analytics)
- Advertising networks and marketing companies  
- Business partners, affiliates, subsidiaries
- Service providers who access user data
- Government agencies (if mentioned)
- If NO external sharing is mentioned, return an empty array []

**BE VERY STRICT**: 
- ANY external data sharing significantly reduces privacy score
- Long data retention (>2 years) is a major privacy concern
- Internal analytics with short retention (30-90 days) is acceptable
- External analytics sharing (Google Analytics, etc.) should lower the score
- User data deletion should be possible and clearly explained
"""
    
    async def analyze_terms_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Analyze terms & conditions by URL (AI fetches content)
        Returns: Analysis dict or None if failed
        """
        logger.info(f"AI Service: Starting analyze_terms_by_url for {url}")
        
        # Ensure the AI service is initialized
        self._ensure_initialized()
        
        if not self.model:
            logger.error("AI model not initialized - GEMINI_API_KEY missing or invalid")
            return None
            
        try:
            prompt = f"{self._get_analysis_prompt()}\n\nPlease analyze the Terms & Conditions at this URL: {url}"
            
            logger.info(f"AI Service: Sending request to Gemini API...")
            
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            response = self.model.generate_content(
                prompt,
                safety_settings=safety_settings,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=2000,
                )
            )
            
            logger.info(f"AI Service: Received response from Gemini API")
            
            if response.text:
                logger.info(f"AI Service: Response text length: {len(response.text)}")
                logger.debug(f"AI Service: Raw response: {response.text[:500]}...")
                
                # Try to extract JSON from response
                import json
                # Look for JSON in the response
                text = response.text.strip()
                
                # Try to parse as direct JSON
                if text.startswith('{') and text.endswith('}'):
                    try:
                        result = json.loads(text)
                        logger.info("AI Service: Successfully parsed response as direct JSON")
                        return result
                    except json.JSONDecodeError as e:
                        logger.warning(f"AI Service: Failed to parse as direct JSON: {e}")
                
                # Try to find JSON block in markdown
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(1))
                        logger.info("AI Service: Successfully parsed JSON from markdown block")
                        return result
                    except json.JSONDecodeError as e:
                        logger.warning(f"AI Service: Failed to parse JSON from markdown: {e}")
                
                # Try to find JSON without markdown
                json_match = re.search(r'(\{[^{}]*"privacy_score"[^{}]*\})', text, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(1))
                        logger.info("AI Service: Successfully parsed JSON from text search")
                        return result
                    except json.JSONDecodeError as e:
                        logger.warning(f"AI Service: Failed to parse JSON from text search: {e}")
                
                # If no valid JSON found, return the raw text
                logger.warning("AI Service: Could not parse AI response as JSON, returning fallback")
                return {
                    "privacy_score": 50,
                    "score_explanation": "Could not parse structured response",
                    "summary": text[:500] + "..." if len(text) > 500 else text,
                    "error": "Response parsing failed"
                }
            else:
                logger.error("AI Service: No response text received from Gemini")
            
            return None
            
        except Exception as e:
            logger.error(f"AI Service: Error analyzing terms by URL {url}: {str(e)}")
            logger.error(f"AI Service: Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"AI Service: Full traceback: {traceback.format_exc()}")
            return None
    
    async def analyze_terms_by_text(self, text: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Analyze terms & conditions by providing the text content
        Returns: Analysis dict or None if failed
        """
        logger.info(f"AI Service: Starting analyze_terms_by_text for {url}")
        
        # Ensure the AI service is initialized
        self._ensure_initialized()
        
        if not self.model:
            logger.error("AI model not initialized - GEMINI_API_KEY missing or invalid")
            return None
            
        try:
            prompt = f"{self._get_analysis_prompt()}\n\nPlease analyze these Terms & Conditions from {url}:\n\n{text[:10000]}"  # Limit text size
            
            logger.info(f"AI Service: Sending text analysis request to Gemini API...")
            logger.info(f"AI Service: Text length: {len(text)} characters (limited to 10000)")
            
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            response = self.model.generate_content(
                prompt,
                safety_settings=safety_settings,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=2000,
                )
            )
            
            logger.info(f"AI Service: Received text analysis response from Gemini API")
            
            if response.text:
                logger.info(f"AI Service: Text analysis response length: {len(response.text)}")
                logger.debug(f"AI Service: Raw text analysis response: {response.text[:500]}...")
                
                # Try to extract JSON from response
                import json
                text = response.text.strip()
                
                # Try to parse as direct JSON
                if text.startswith('{') and text.endswith('}'):
                    try:
                        result = json.loads(text)
                        logger.info("AI Service: Successfully parsed text analysis as direct JSON")
                        return result
                    except json.JSONDecodeError as e:
                        logger.warning(f"AI Service: Failed to parse text analysis as direct JSON: {e}")
                
                # Try to find JSON block in markdown
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(1))
                        logger.info("AI Service: Successfully parsed text analysis JSON from markdown")
                        return result
                    except json.JSONDecodeError as e:
                        logger.warning(f"AI Service: Failed to parse text analysis JSON from markdown: {e}")
                
                # Try to find JSON without markdown
                json_match = re.search(r'(\{[^{}]*"privacy_score"[^{}]*\})', text, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(1))
                        logger.info("AI Service: Successfully parsed text analysis JSON from search")
                        return result
                    except json.JSONDecodeError as e:
                        logger.warning(f"AI Service: Failed to parse text analysis JSON from search: {e}")
                
                # If no valid JSON found, return the raw text
                logger.warning("AI Service: Could not parse text analysis response as JSON, returning fallback")
                return {
                    "privacy_score": 50,
                    "score_explanation": "Could not parse structured response",
                    "summary": text[:500] + "..." if len(text) > 500 else text,
                    "error": "Response parsing failed"
                }
            else:
                logger.error("AI Service: No response text received from Gemini for text analysis")
            
            return None
            
        except Exception as e:
            logger.error(f"AI Service: Error analyzing terms by text: {str(e)}")
            logger.error(f"AI Service: Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"AI Service: Full traceback: {traceback.format_exc()}")
            return None


# Global instance
ai_service = AIAnalysisService()
