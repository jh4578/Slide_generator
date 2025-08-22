"""
Enhanced Orchestrator for FRESCO HTML Generation
Main entry point that automatically decides between single-page and multi-page processing
"""

import logging
import time
from typing import Dict, Any, Optional

from multi_page_orchestrator import MultiPageOrchestrator
from orchestrator import FrescoHTMLOrchestrator
from chains.page_planner import PagePlannerAgent
from config import config

logger = logging.getLogger(__name__)

class EnhancedFrescoOrchestrator:
    """
    Enhanced orchestrator that automatically handles both single and multi-page scenarios
    Acts as the main entry point for all HTML generation requests
    """
    
    def __init__(self):
        """Initialize the enhanced orchestrator"""
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.page_planner = PagePlannerAgent()
        self.multi_page_orchestrator = MultiPageOrchestrator()
        self.single_page_orchestrator = FrescoHTMLOrchestrator()
        
        self.logger.info("EnhancedFrescoOrchestrator initialized")
    
    def process_query(self, user_query: str, save_html: bool = True, 
                     filename: str = None, force_single_page: bool = False) -> Dict[str, Any]:
        """
        Main processing method that automatically decides between single and multi-page
        
        Args:
            user_query: User's original query
            save_html: Whether to save output to file
            filename: Optional filename for output
            force_single_page: Force single page processing even if multi-page is detected
            
        Returns:
            Complete processing results
        """
        start_time = time.time()
        self.logger.info(f"Processing query with enhanced orchestrator: {user_query}")
        
        try:
            # Quick check for obvious single-page scenarios
            if force_single_page or self._is_obviously_single_page(user_query):
                self.logger.info("Using single-page processing (forced or obvious single-page)")
                result = self.single_page_orchestrator.process_query(
                    user_query, save_html, filename
                )
                result['is_multi_page'] = False
                result['orchestrator_used'] = 'single_page'
                return result
            
            # Use page planner to analyze the query
            self.logger.info("Analyzing query for page planning...")
            page_plan = self.page_planner.analyze_query(user_query)
            
            # Decide which orchestrator to use
            if page_plan.is_multi_page and page_plan.total_pages > 1:
                self.logger.info(f"Using multi-page processing: {page_plan.total_pages} pages")
                result = self.multi_page_orchestrator.process_query(
                    user_query, save_html, filename
                )
                result['orchestrator_used'] = 'multi_page'
            else:
                self.logger.info("Using single-page processing based on analysis")
                result = self.single_page_orchestrator.process_query(
                    user_query, save_html, filename
                )
                result['is_multi_page'] = False
                result['orchestrator_used'] = 'single_page'
            
            return result
            
        except Exception as e:
            self.logger.error(f"Enhanced orchestrator failed: {str(e)}")
            # Fallback to single-page processing
            self.logger.info("Falling back to single-page processing due to error")
            try:
                result = self.single_page_orchestrator.process_query(
                    user_query, save_html, filename
                )
                result['is_multi_page'] = False
                result['orchestrator_used'] = 'single_page_fallback'
                result['fallback_reason'] = str(e)
                return result
            except Exception as fallback_error:
                return {
                    'success': False,
                    'user_query': user_query,
                    'error': f"Both multi-page and single-page processing failed. Original: {str(e)}, Fallback: {str(fallback_error)}",
                    'processing_time': {'total': time.time() - start_time},
                    'orchestrator_used': 'failed'
                }
    
    def _is_obviously_single_page(self, user_query: str) -> bool:
        """
        Quick heuristic check for obvious single-page queries
        Helps avoid unnecessary LLM calls for simple cases
        
        Args:
            user_query: User's query
            
        Returns:
            True if obviously single-page
        """
        query_lower = user_query.lower()
        
        # Single question indicators
        single_page_indicators = [
            'what is',
            'show me',
            'tell me about',
            'explain',
            'describe',
            'how does',
            'when does',
            'where is',
            'why does'
        ]
        
        # Multi-page indicators (if present, don't use single-page)
        multi_page_indicators = [
            'presentation',
            'slides',
            'pages',
            'comprehensive',
            'overview covering',
            'analysis of',
            'and',  # Often indicates multiple topics
            'complete analysis',
            'full report'
        ]
        
        # Check for multi-page indicators first
        for indicator in multi_page_indicators:
            if indicator in query_lower:
                return False
        
        # Check for single-page indicators
        for indicator in single_page_indicators:
            if query_lower.startswith(indicator):
                return True
        
        # Check query length (very short queries are usually single-page)
        if len(query_lower.split()) <= 5:
            return True
        
        return False
    
    def process_query_steps(self, user_query: str) -> Dict[str, Any]:
        """
        Process query with detailed step information
        Always uses single-page orchestrator for detailed analysis
        
        Args:
            user_query: User's question
            
        Returns:
            Dictionary with detailed step results
        """
        self.logger.info(f"Processing query with detailed steps: {user_query}")
        return self.single_page_orchestrator.process_query_steps(user_query)
    
    def search_evidence_only(self, user_query: str) -> list:
        """
        Search for evidence without HTML generation
        Uses single-page orchestrator for this utility function
        
        Args:
            user_query: User's search query
            
        Returns:
            List of relevant evidence items
        """
        return self.single_page_orchestrator.search_evidence_only(user_query)
    
    def generate_html_from_evidence(self, user_query: str, evidence_results: list,
                                   save_to_file: bool = True, filename: str = None) -> Dict[str, Any]:
        """
        Generate HTML from pre-selected evidence
        Uses single-page orchestrator for this utility function
        
        Args:
            user_query: Original user query
            evidence_results: Pre-selected evidence items
            save_to_file: Whether to save to file
            filename: Output filename
            
        Returns:
            Dictionary with HTML generation results
        """
        return self.single_page_orchestrator.generate_html_from_evidence(
            user_query, evidence_results, save_to_file, filename
        )
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status for all components
        
        Returns:
            Dictionary with system status information
        """
        status = {
            'enhanced_orchestrator': 'initialized',
            'components': {},
            'config': {}
        }
        
        try:
            # Get single-page orchestrator status
            single_page_status = self.single_page_orchestrator.get_system_status()
            status['components']['single_page'] = single_page_status
            
            # Check page planner
            status['components']['page_planner'] = {
                'status': 'ready',
                'available': True
            }
            
            # Check multi-page orchestrator
            status['components']['multi_page'] = {
                'status': 'ready',
                'max_concurrent_pages': self.multi_page_orchestrator.max_concurrent_pages
            }
            
            # Add configuration info
            status['config'] = {
                'embedding_model': config.embedding_model,
                'llm_model': config.llm_model,
                'supports_multi_page': True,
                'auto_page_detection': True
            }
            
        except Exception as e:
            status['error'] = str(e)
        
        return status
    
    def force_single_page_processing(self, user_query: str, save_html: bool = True,
                                   filename: str = None) -> Dict[str, Any]:
        """
        Force single-page processing regardless of query content
        
        Args:
            user_query: User's query
            save_html: Whether to save HTML
            filename: Optional filename
            
        Returns:
            Single-page processing results
        """
        self.logger.info(f"Forcing single-page processing for: {user_query}")
        result = self.single_page_orchestrator.process_query(user_query, save_html, filename)
        result['is_multi_page'] = False
        result['orchestrator_used'] = 'single_page_forced'
        return result
    
    def force_multi_page_processing(self, user_query: str, save_html: bool = True,
                                  filename: str = None) -> Dict[str, Any]:
        """
        Force multi-page processing regardless of query content
        
        Args:
            user_query: User's query
            save_html: Whether to save output
            filename: Optional filename
            
        Returns:
            Multi-page processing results
        """
        self.logger.info(f"Forcing multi-page processing for: {user_query}")
        result = self.multi_page_orchestrator.process_query(user_query, save_html, filename)
        result['orchestrator_used'] = 'multi_page_forced'
        return result 