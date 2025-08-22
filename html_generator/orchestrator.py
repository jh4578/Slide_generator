"""
Main Orchestrator for FRESCO study HTML generation
Coordinates query expansion, semantic search, and HTML generation chains
"""

from typing import Dict, Any, List
import logging
import time

from chains import QueryExpanderChain, SemanticSearchChain, ImageGeneratorChain, HTMLGeneratorChain
from config import config

logger = logging.getLogger(__name__)

class FrescoHTMLOrchestrator:
    """
    Main orchestrator for FRESCO study HTML generation pipeline
    Coordinates the complete workflow from user query to HTML output
    """
    
    def __init__(self):
        """Initialize all chain components"""
        # Setup logging
        config.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("Initializing FRESCO HTML Orchestrator...")
        
        # Initialize all chains
        try:
            self.query_expander = QueryExpanderChain()
            self.semantic_searcher = SemanticSearchChain()
            self.image_generator = ImageGeneratorChain()
            self.html_generator = HTMLGeneratorChain()
            
            self.logger.info("All chains initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize orchestrator: {e}")
            raise
    
    def process_query(self, user_query: str, save_html: bool = True, 
                     filename: str = None) -> Dict[str, Any]:
        """
        Process a complete user query through the entire pipeline
        Args:
            user_query: User's question about FRESCO study
            save_html: Whether to save HTML to file
            filename: Output filename (optional)
        Returns:
            Dictionary with complete processing results
        """
        start_time = time.time()
        self.logger.info(f"Processing query: {user_query}")
        
        try:
            # Step 1: Query Expansion
            self.logger.info("Step 1: Expanding user query...")
            query_expansion_start = time.time()
            
            expansion_result = self.query_expander.expand_query(user_query)
            expanded_queries = expansion_result.get('all_queries', [user_query])
            
            query_expansion_time = time.time() - query_expansion_start
            self.logger.info(f"Query expansion completed in {query_expansion_time:.2f}s")
            self.logger.info(f"Generated {len(expanded_queries)} query variations")
            
            # Step 2: Semantic Search
            self.logger.info("Step 2: Searching for relevant evidence...")
            search_start = time.time()
            
            evidence_results = self.semantic_searcher.search_evidence(expanded_queries)
            
            search_time = time.time() - search_start
            self.logger.info(f"Semantic search completed in {search_time:.2f}s")
            self.logger.info(f"Found {len(evidence_results)} relevant evidence items")
            
            # Step 3: Image Processing (conditional)
            self.logger.info("Step 3: Processing images...")
            image_processing_start = time.time()
            
            image_results = self.image_generator.process_images(user_query, evidence_results)
            
            image_processing_time = time.time() - image_processing_start
            self.logger.info(f"Image processing completed in {image_processing_time:.2f}s")
            self.logger.info(f"Images found: {image_results.get('image_count', 0)}, "
                           f"relevant: {image_results.get('relevant_images', 0)}, "
                           f"generation needed: {image_results.get('should_generate', False)}")
            
            # Step 4: HTML Generation
            self.logger.info("Step 4: Generating HTML content...")
            generation_start = time.time()
            
            html_content = self.html_generator.create_complete_html(
                user_query, evidence_results, image_results
            )
            
            generation_time = time.time() - generation_start
            self.logger.info(f"HTML generation completed in {generation_time:.2f}s")
            
            # Step 5: Save evidence and HTML (optional)
            evidence_path = None
            output_path = None
            if save_html:
                self.logger.info("Step 5: Saving evidence and HTML to file...")
                evidence_path = self._save_evidence_to_file(user_query, evidence_results, expanded_queries)
                output_path = self.html_generator.save_html_to_file(html_content, filename)
            
            # Prepare complete result
            total_time = time.time() - start_time
            
            result = {
                'success': True,
                'user_query': user_query,
                'expanded_queries': expanded_queries,
                'evidence_count': len(evidence_results),
                'evidence_results': evidence_results,
                'html_content': html_content,
                'output_path': output_path,
                'evidence_path': evidence_path,
                'processing_time': {
                    'query_expansion': query_expansion_time,
                    'semantic_search': search_time,
                    'image_processing': image_processing_time,
                    'html_generation': generation_time,
                    'total': total_time
                },
                'image_results': image_results,
                'evidence_summary': self.semantic_searcher.get_top_evidence_summary(evidence_results)
            }
            
            self.logger.info(f"Pipeline completed successfully in {total_time:.2f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"Pipeline processing failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'user_query': user_query,
                'error': str(e),
                'processing_time': {'total': time.time() - start_time}
            }
    
    def process_query_steps(self, user_query: str) -> Dict[str, Any]:
        """
        Process query with detailed step-by-step results
        Useful for debugging and analysis
        Args:
            user_query: User's question
        Returns:
            Dictionary with detailed step results
        """
        self.logger.info(f"Processing query with detailed steps: {user_query}")
        
        results = {
            'user_query': user_query,
            'steps': {}
        }
        
        try:
            # Step 1: Query Expansion
            self.logger.info("Detailed Step 1: Query Expansion")
            expansion_result = self.query_expander.expand_query(user_query)
            results['steps']['query_expansion'] = expansion_result
            
            # Step 2: Semantic Search
            self.logger.info("Detailed Step 2: Semantic Search")
            expanded_queries = expansion_result.get('all_queries', [user_query])
            evidence_results = self.semantic_searcher.search_evidence(expanded_queries)
            
            results['steps']['semantic_search'] = {
                'evidence_count': len(evidence_results),
                'evidence_results': evidence_results,
                'evidence_summary': self.semantic_searcher.get_top_evidence_summary(evidence_results)
            }
            
            # Step 3: Image Processing
            self.logger.info("Detailed Step 3: Image Processing")
            image_results = self.image_generator.process_images(user_query, evidence_results)
            results['steps']['image_processing'] = image_results
            
            # Step 4: HTML Content Generation (content only, not full page)
            self.logger.info("Detailed Step 4: HTML Content Generation")
            content_result = self.html_generator.generate_html_content(user_query, evidence_results, image_results)
            results['steps']['html_generation'] = content_result
            
            results['success'] = True
            self.logger.info("Detailed step processing completed successfully")
            
        except Exception as e:
            self.logger.error(f"Detailed step processing failed: {str(e)}")
            results['success'] = False
            results['error'] = str(e)
        
        return results
    
    def search_evidence_only(self, user_query: str) -> List[Dict[str, Any]]:
        """
        Convenience method to search for evidence without HTML generation
        Args:
            user_query: User's search query
        Returns:
            List of relevant evidence items
        """
        self.logger.info(f"Searching evidence for: {user_query}")
        
        try:
            # Expand query and search
            expanded_queries = self.query_expander.get_query_variations(user_query)
            evidence_results = self.semantic_searcher.search_evidence(expanded_queries)
            
            self.logger.info(f"Found {len(evidence_results)} evidence items")
            return evidence_results
            
        except Exception as e:
            self.logger.error(f"Evidence search failed: {str(e)}")
            return []
    
    def generate_html_from_evidence(self, user_query: str, 
                                   evidence_results: List[Dict[str, Any]], 
                                   save_to_file: bool = True,
                                   filename: str = None) -> Dict[str, Any]:
        """
        Generate HTML from pre-selected evidence
        Args:
            user_query: Original user query
            evidence_results: Pre-selected evidence items
            save_to_file: Whether to save to file
            filename: Output filename
        Returns:
            Dictionary with HTML generation results
        """
        self.logger.info(f"Generating HTML from {len(evidence_results)} evidence items")
        
        try:
            # Process images first
            image_results = self.image_generator.process_images(user_query, evidence_results)
            
            # Generate complete HTML
            html_content = self.html_generator.create_complete_html(user_query, evidence_results, image_results)
            
            # Save if requested
            output_path = None
            if save_to_file:
                output_path = self.html_generator.save_html_to_file(html_content, filename)
            
            return {
                'success': True,
                'html_content': html_content,
                'output_path': output_path,
                'evidence_count': len(evidence_results)
            }
            
        except Exception as e:
            self.logger.error(f"HTML generation from evidence failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get status of all system components
        Returns:
            Dictionary with system status information
        """
        status = {
            'orchestrator': 'initialized',
            'components': {},
            'config': {}
        }
        
        try:
            # Check query expander
            status['components']['query_expander'] = {
                'status': 'ready',
                'expansion_count': self.query_expander.expansion_count
            }
            
            # Check semantic searcher
            status['components']['semantic_searcher'] = {
                'status': 'ready',
                'faiss_vectors': self.semantic_searcher.faiss_index.ntotal,
                'evidence_count': len(self.semantic_searcher.evidence_list),
                'top_k': self.semantic_searcher.top_k
            }
            
            # Check image generator
            status['components']['image_generator'] = {
                'status': 'ready',
                'vision_enabled': True,
                'templates_available': len([f for f in os.listdir(self.image_generator.templates_dir) if f.endswith('.png')]) if hasattr(self.image_generator, 'templates_dir') else 0
            }
            
            # Check HTML generator
            status['components']['html_generator'] = {
                'status': 'ready',
                'template_loaded': bool(self.html_generator.template_content)
            }
            
            # Add configuration info
            status['config'] = {
                'embedding_model': config.embedding_model,
                'llm_model': config.llm_model,
                'top_k_results': config.top_k_results
            }
            
        except Exception as e:
            status['error'] = str(e)
        
        return status
    
    def _save_evidence_to_file(self, user_query: str, evidence_results: List[Dict[str, Any]], 
                              expanded_queries: List[str]) -> str:
        """
        Save evidence results to a JSON file
        Args:
            user_query: Original user query
            evidence_results: List of evidence items found
            expanded_queries: List of expanded query variations
        Returns:
            Path to saved evidence file
        """
        import json
        import os
        from datetime import datetime
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(config.html_generator_root, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename based on query and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = "".join(c for c in user_query if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_query = safe_query.replace(' ', '_')[:30]  # Limit length
        filename = f"evidence_{safe_query}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Prepare evidence data
        evidence_data = {
            "query_info": {
                "original_query": user_query,
                "expanded_queries": expanded_queries,
                "search_timestamp": datetime.now().isoformat(),
                "total_results": len(evidence_results)
            },
            "evidence_summary": {
                "total_count": len(evidence_results),
                "type_distribution": {},
                "source_distribution": {},
                "avg_similarity_score": 0
            },
            "evidence_results": evidence_results
        }
        
        # Calculate summary statistics
        if evidence_results:
            # Type distribution
            for evidence in evidence_results:
                category = evidence.get('category', 'unknown')
                evidence_data["evidence_summary"]["type_distribution"][category] = \
                    evidence_data["evidence_summary"]["type_distribution"].get(category, 0) + 1
            
            # Source distribution
            for evidence in evidence_results:
                source = evidence.get('source_document', 'unknown')
                evidence_data["evidence_summary"]["source_distribution"][source] = \
                    evidence_data["evidence_summary"]["source_distribution"].get(source, 0) + 1
            
            # Average similarity score
            scores = [e.get('similarity_score', 0) for e in evidence_results if 'similarity_score' in e]
            if scores:
                evidence_data["evidence_summary"]["avg_similarity_score"] = sum(scores) / len(scores)
        
        # Save to file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(evidence_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Evidence saved to: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to save evidence: {e}")
            return None 