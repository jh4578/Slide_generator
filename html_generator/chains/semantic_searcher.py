"""
Semantic Search Chain for FRESCO study evidence
Searches through pre-computed embeddings using FAISS for relevant evidence
"""

from typing import List, Dict, Any, Tuple
import numpy as np
import faiss
import pickle
from openai import OpenAI
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

logger = logging.getLogger(__name__)

class SemanticSearchChain:
    """
    LangChain component for semantic search of FRESCO study evidence
    Uses pre-computed FAISS index for efficient similarity search
    """
    
    def __init__(self):
        """Initialize the semantic searcher with FAISS index and metadata"""
        # Setup logging
        config.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Get OpenAI configuration for embeddings
        openai_config = config.get_openai_config()
        self.client = OpenAI(api_key=openai_config['api_key'])
        self.embedding_model = openai_config['embedding_model']
        
        # Get search configuration
        search_config = config.get_search_config()
        self.top_k = search_config['top_k']
        self.similarity_threshold = search_config['threshold']
        
        # Load FAISS index and metadata
        self._load_faiss_index()
        self._load_metadata()
        
        self.logger.info("SemanticSearchChain initialized successfully")
    
    def _load_faiss_index(self):
        """Load the pre-computed FAISS index"""
        try:
            self.faiss_index = faiss.read_index(config.faiss_index_path)
            self.logger.info(f"FAISS index loaded: {self.faiss_index.ntotal} vectors")
        except Exception as e:
            self.logger.error(f"Failed to load FAISS index: {e}")
            raise
    
    def _load_metadata(self):
        """Load evidence metadata"""
        try:
            with open(config.metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            
            self.evidence_list = self.metadata['evidence_list']
            self.type_weights = self.metadata['type_weights']
            
            self.logger.info(f"Metadata loaded: {len(self.evidence_list)} evidence items")
        except Exception as e:
            self.logger.error(f"Failed to load metadata: {e}")
            raise
    
    def _get_query_embedding(self, query: str) -> np.ndarray:
        """
        Generate embedding for a single query
        Args:
            query: Query string
        Returns:
            Normalized embedding vector
        """
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=[query]
            )
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            
            # Normalize the embedding
            embedding = embedding.reshape(1, -1)
            faiss.normalize_L2(embedding)
            
            return embedding.flatten()
        except Exception as e:
            self.logger.error(f"Failed to generate embedding for query: {e}")
            raise
    
    def _search_single_query(self, query: str, k: int = None) -> List[Tuple[int, float]]:
        """
        Search FAISS index for a single query
        Args:
            query: Search query
            k: Number of results to return
        Returns:
            List of (evidence_index, similarity_score) tuples
        """
        k = k or self.top_k
        
        # Generate query embedding
        query_embedding = self._get_query_embedding(query)
        
        # Search FAISS index
        scores, indices = self.faiss_index.search(
            query_embedding.reshape(1, -1), k * 2  # Get more results for filtering
        )
        
        # Filter by similarity threshold and return
        results = []
        for i, (idx, score) in enumerate(zip(indices[0], scores[0])):
            if idx != -1 and score >= self.similarity_threshold:
                results.append((int(idx), float(score)))
        
        return results[:k]  # Return top k results
    
    def _merge_search_results(self, all_results: List[List[Tuple[int, float]]]) -> List[Tuple[int, float]]:
        """
        Merge and rank results from multiple query searches
        Args:
            all_results: List of search results from different queries
        Returns:
            Merged and ranked results
        """
        # Combine all results
        combined_scores = {}
        
        for query_results in all_results:
            for idx, score in query_results:
                if idx in combined_scores:
                    # Use maximum score for duplicate evidence
                    combined_scores[idx] = max(combined_scores[idx], score)
                else:
                    combined_scores[idx] = score
        
        # Apply type weights
        weighted_scores = {}
        for idx, score in combined_scores.items():
            evidence = self.evidence_list[idx]
            
            # Check if this is an image type and apply special weight
            if evidence.get('type') == 'image':
                # For images, use the image-specific weight
                weight = self.type_weights.get('extracted_image', 1.0)
            else:
                # For other types, use category-based weight
                category = evidence.get('category', 'general')
                weight = self.type_weights.get(category, 1.0)
            
            weighted_scores[idx] = score * weight
        
        # Sort by weighted score
        sorted_results = sorted(
            weighted_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return [(idx, score) for idx, score in sorted_results[:self.top_k]]
    
    def search_evidence(self, queries: List[str]) -> List[Dict[str, Any]]:
        """
        Search for evidence using multiple query variations
        Args:
            queries: List of query variations
        Returns:
            List of relevant evidence items with scores
        """
        self.logger.info(f"Searching evidence with {len(queries)} queries")
        
        try:
            # Search with each query
            all_results = []
            for query in queries:
                query_results = self._search_single_query(query)
                all_results.append(query_results)
                self.logger.debug(f"Query '{query}' found {len(query_results)} results")
            
            # Merge and rank results
            final_results = self._merge_search_results(all_results)
            
            # Convert to evidence objects with scores
            evidence_results = []
            for idx, score in final_results:
                evidence = self.evidence_list[idx].copy()
                evidence['similarity_score'] = score
                evidence['search_rank'] = len(evidence_results) + 1
                evidence_results.append(evidence)
            
            self.logger.info(f"Retrieved {len(evidence_results)} relevant evidence items")
            return evidence_results
            
        except Exception as e:
            self.logger.error(f"Evidence search failed: {e}")
            return []
    
    def search_with_single_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Convenience method for searching with a single query
        Args:
            query: Single search query
        Returns:
            List of relevant evidence items
        """
        return self.search_evidence([query])
    
    def get_evidence_by_type(self, evidence_results: List[Dict[str, Any]], 
                           evidence_type: str) -> List[Dict[str, Any]]:
        """
        Filter evidence results by type
        Args:
            evidence_results: List of evidence items
            evidence_type: Type to filter by (e.g., 'extracted_image', 'table')
        Returns:
            Filtered evidence list
        """
        return [
            evidence for evidence in evidence_results 
            if evidence.get('category') == evidence_type
        ]
    
    def get_top_evidence_summary(self, evidence_results: List[Dict[str, Any]], 
                                top_n: int = 5) -> Dict[str, Any]:
        """
        Get summary of top evidence results
        Args:
            evidence_results: List of evidence items
            top_n: Number of top items to summarize
        Returns:
            Summary dictionary
        """
        top_results = evidence_results[:top_n]
        
        # Count by type
        type_counts = {}
        sources = set()
        
        for evidence in top_results:
            category = evidence.get('category', 'unknown')
            type_counts[category] = type_counts.get(category, 0) + 1
            
            source = evidence.get('source_document', 'unknown')
            sources.add(source)
        
        return {
            'total_results': len(evidence_results),
            'top_n_count': len(top_results),
            'type_distribution': type_counts,
            'source_documents': list(sources),
            'avg_similarity_score': np.mean([e.get('similarity_score', 0) for e in top_results]) if top_results else 0
        } 