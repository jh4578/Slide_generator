"""
PagePlannerAgent for analyzing user queries and planning multi-page presentations
Determines if a query requires multiple pages and creates a structured page plan
"""

import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import openai
from config import config

logger = logging.getLogger(__name__)

@dataclass
class PageInfo:
    """Information about a single page in the presentation"""
    page_number: int
    title: str
    content_focus: str
    specific_query: str
    priority: int = 1  # 1 = high, 2 = medium, 3 = low

@dataclass 
class PagePlan:
    """Complete plan for multi-page presentation"""
    is_multi_page: bool
    total_pages: int
    overall_theme: str
    pages: List[PageInfo]
    reasoning: str

class PagePlannerAgent:
    """
    Agent responsible for analyzing user queries and determining page structure
    Uses LLM to intelligently plan multi-page presentations
    """
    
    def __init__(self):
        """Initialize the page planner agent"""
        self.logger = logging.getLogger(__name__)
        self.client = openai.OpenAI(api_key=config.openai_api_key)
        self.logger.info("PagePlannerAgent initialized")
    
    def analyze_query(self, user_query: str) -> PagePlan:
        """
        Analyze user query to determine if multi-page presentation is needed
        
        Args:
            user_query: The user's original query
            
        Returns:
            PagePlan object with analysis results
        """
        self.logger.info(f"Analyzing query for page planning: {user_query}")
        
        try:
            # Create prompt for LLM analysis
            system_prompt = self._get_analysis_system_prompt()
            user_prompt = self._get_analysis_user_prompt(user_query)
            
            # Call LLM for analysis
            response = self.client.chat.completions.create(
                model=config.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            page_plan = self._parse_llm_response(response_text, user_query)
            
            self.logger.info(f"Page analysis complete: {page_plan.total_pages} pages planned")
            return page_plan
            
        except Exception as e:
            self.logger.error(f"Error in query analysis: {str(e)}")
            # Return single page plan as fallback
            return self._create_single_page_fallback(user_query)
    
    def _get_analysis_system_prompt(self) -> str:
        """Get the system prompt for page planning analysis"""
        return """You are an expert medical presentation planner for FRESCO study data. 
Your job is to analyze user queries and determine if they require single or multiple pages.

GUIDELINES FOR MULTI-PAGE DECISIONS:
- Multi-page is needed when user explicitly mentions:
  * Multiple topics (e.g., "efficacy and safety", "overview covering X, Y, Z")
  * Specific page numbers (e.g., "3-page presentation", "slides about")
  * Comprehensive coverage (e.g., "complete analysis", "full overview")
  * Multiple data types (e.g., "demographics, efficacy, and adverse events")

- Single page is sufficient for:
  * Specific single questions (e.g., "What is the overall survival?")
  * Single topic queries (e.g., "FRESCO safety data")
  * Simple data requests

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{
  "is_multi_page": boolean,
  "total_pages": number,
  "overall_theme": "string",
  "reasoning": "string explaining decision",
  "pages": [
    {
      "page_number": 1,
      "title": "string",
      "content_focus": "string describing main focus",
      "specific_query": "string - specific query for this page",
      "priority": 1
    }
  ]
}

For FRESCO study, common page topics include:
- Study Overview/Background
- Patient Demographics/Baseline Characteristics  
- Efficacy Data (Overall Survival, Progression-Free Survival)
- Safety Profile/Adverse Events
- Mechanism of Action
- Clinical Implications/Conclusions"""

    def _get_analysis_user_prompt(self, user_query: str) -> str:
        """Get the user prompt for page planning analysis"""
        return f"""Analyze this query and determine if it needs multiple pages:

USER QUERY: "{user_query}"

Consider:
1. Does the query explicitly mention multiple topics or pages?
2. Would a comprehensive answer require multiple distinct sections?
3. Is this a single focused question or a broader request?

Provide your analysis in the specified JSON format."""

    def _parse_llm_response(self, response_text: str, original_query: str) -> PagePlan:
        """
        Parse LLM response into PagePlan object
        
        Args:
            response_text: Raw response from LLM
            original_query: Original user query for fallback
            
        Returns:
            PagePlan object
        """
        try:
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['is_multi_page', 'total_pages', 'overall_theme', 'pages', 'reasoning']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Create PageInfo objects
            pages = []
            for page_data in data['pages']:
                page_info = PageInfo(
                    page_number=page_data.get('page_number', 1),
                    title=page_data.get('title', ''),
                    content_focus=page_data.get('content_focus', ''),
                    specific_query=page_data.get('specific_query', original_query),
                    priority=page_data.get('priority', 1)
                )
                pages.append(page_info)
            
            # Create PagePlan
            page_plan = PagePlan(
                is_multi_page=data['is_multi_page'],
                total_pages=data['total_pages'],
                overall_theme=data['overall_theme'],
                pages=pages,
                reasoning=data['reasoning']
            )
            
            return page_plan
            
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {str(e)}")
            self.logger.error(f"Response text: {response_text}")
            return self._create_single_page_fallback(original_query)
    
    def _create_single_page_fallback(self, user_query: str) -> PagePlan:
        """
        Create a single-page fallback plan when analysis fails
        
        Args:
            user_query: Original user query
            
        Returns:
            Single-page PagePlan
        """
        self.logger.info("Creating single-page fallback plan")
        
        page_info = PageInfo(
            page_number=1,
            title="FRESCO Study Analysis",
            content_focus="Comprehensive response to user query",
            specific_query=user_query,
            priority=1
        )
        
        return PagePlan(
            is_multi_page=False,
            total_pages=1,
            overall_theme="FRESCO Study Data Analysis",
            pages=[page_info],
            reasoning="Fallback to single page due to analysis error or simple query"
        )
    
    def validate_page_plan(self, page_plan: PagePlan) -> bool:
        """
        Validate that the page plan is reasonable and executable
        
        Args:
            page_plan: PagePlan to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check basic structure
            if not isinstance(page_plan, PagePlan):
                return False
            
            # Check page count consistency
            if page_plan.total_pages != len(page_plan.pages):
                self.logger.warning("Page count mismatch, adjusting...")
                page_plan.total_pages = len(page_plan.pages)
            
            # Check reasonable page limits (1-10 pages)
            if page_plan.total_pages < 1 or page_plan.total_pages > 10:
                self.logger.warning(f"Unreasonable page count: {page_plan.total_pages}")
                return False
            
            # Check each page has required fields
            for page in page_plan.pages:
                if not page.title or not page.specific_query:
                    self.logger.warning("Page missing required fields")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating page plan: {str(e)}")
            return False
    
    def get_single_page_plan(self, user_query: str) -> PagePlan:
        """
        Create a simple single-page plan without LLM analysis
        Useful for known single-page queries
        
        Args:
            user_query: User's query
            
        Returns:
            Single-page PagePlan
        """
        page_info = PageInfo(
            page_number=1,
            title="FRESCO Study Response",
            content_focus="Direct response to user query",
            specific_query=user_query,
            priority=1
        )
        
        return PagePlan(
            is_multi_page=False,
            total_pages=1,
            overall_theme="FRESCO Study Analysis",
            pages=[page_info],
            reasoning="Single focused query"
        ) 