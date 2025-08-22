#!/usr/bin/env python3
"""
Embedding preprocessing script for FRESCO study evidence
Converts evidence from extracted_content.json into vectors and stores in FAISS database
This script should be run only once unless source data is updated
"""

import json
import os
import numpy as np
from typing import List, Dict, Any
import faiss
from openai import OpenAI
from tqdm import tqdm
import pickle
import logging

from config import config

class EvidenceEmbeddingProcessor:
    def __init__(self):
        """
        Initialize embedding processor with configuration
        Uses config module for all settings and API credentials
        """
        # Setup logging
        config.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize OpenAI client
        openai_config = config.get_openai_config()
        self.client = OpenAI(api_key=openai_config['api_key'])
        
        # Get embedding configuration
        embedding_config = config.get_embedding_config()
        self.embedding_model = embedding_config['model']
        self.embedding_dimension = embedding_config['dimension']
        self.batch_size = embedding_config['batch_size']
        self.type_weights = embedding_config['type_weights']
        
        # File paths from config
        self.extracted_content_path = config.extracted_content_path
        self.embeddings_dir = config.embeddings_dir
        self.faiss_index_path = config.faiss_index_path
        self.metadata_path = config.metadata_path
        
    def create_output_directory(self):
        """Create output directory for embeddings"""
        if not os.path.exists(self.embeddings_dir):
            os.makedirs(self.embeddings_dir)
            self.logger.info(f"Created output directory: {self.embeddings_dir}")
    
    def load_evidence_data(self) -> List[Dict[str, Any]]:
        """
        Load evidence data from extracted_content.json
        Returns:
            List of evidence objects
        """
        self.logger.info(f"Loading evidence data from: {self.extracted_content_path}")
        
        with open(self.extracted_content_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        evidence_list = data.get('evidence', [])
        self.logger.info(f"Loaded {len(evidence_list)} evidence items")
        
        return evidence_list
    
    def prepare_text_for_embedding(self, evidence: Dict[str, Any]) -> str:
        """
        Prepare text for embedding generation
        Args:
            evidence: Single evidence object
        Returns:
            Processed text string
        """
        text_parts = []
        
        # Handle different types of content
        content = evidence.get('content')
        if content:
            if isinstance(content, str):
                text_parts.append(content)
            elif isinstance(content, dict):
                # Handle structured content (tables, etc.)
                if 'headers' in content and 'rows' in content:
                    # Convert table to text
                    headers = content.get('headers', [])
                    rows = content.get('rows', [])
                    table_text = f"Table with headers: {', '.join(headers)}. "
                    table_text += f"Data: {str(rows)[:500]}"  # Limit length
                    text_parts.append(table_text)
                elif 'markdown' in content:
                    # Handle markdown content
                    text_parts.append(content['markdown'])
                else:
                    # Generic dict handling
                    text_parts.append(str(content)[:500])  # Limit length
        
        # Add label if available
        if evidence.get('label'):
            text_parts.append(f"Label: {evidence['label']}")
        
        # Add type information
        if evidence.get('category'):
            text_parts.append(f"Type: {evidence['category']}")
        
        # Add source information
        if evidence.get('source_document'):
            text_parts.append(f"Source: {evidence['source_document']}")
        
        return " | ".join(text_parts)
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings in batches
        Args:
            texts: List of text strings
        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        
        for i in tqdm(range(0, len(texts), self.batch_size), desc="Generating embeddings"):
            batch = texts[i:i + self.batch_size]
            try:
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=batch
                )
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                self.logger.error(f"Batch {i//self.batch_size + 1} embedding failed: {str(e)}")
                raise
        
        return all_embeddings
    
    def apply_type_weights(self, embeddings: np.ndarray, evidence_list: List[Dict[str, Any]]) -> np.ndarray:
        """
        Apply type weights to embedding vectors
        Args:
            embeddings: Original embedding matrix
            evidence_list: List of evidence objects
        Returns:
            Weighted embedding matrix
        """
        weighted_embeddings = embeddings.copy()
        
        for i, evidence in enumerate(evidence_list):
            category = evidence.get('category', 'general')
            weight = self.type_weights.get(category, 1.0)
            weighted_embeddings[i] = weighted_embeddings[i] * weight
        
        self.logger.info("Type weights applied successfully")
        return weighted_embeddings
    
    def create_faiss_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Create FAISS index for vector search
        Args:
            embeddings: Embedding matrix
        Returns:
            FAISS index object
        """
        self.logger.info("Creating FAISS index...")
        
        # Use IndexFlatIP (inner product search, suitable for normalized embeddings)
        index = faiss.IndexFlatIP(self.embedding_dimension)
        
        # Normalize embedding vectors
        faiss.normalize_L2(embeddings)
        
        # Add vectors to index
        index.add(embeddings)
        
        self.logger.info(f"FAISS index created successfully with {index.ntotal} vectors")
        return index
    
    def save_index_and_metadata(self, index: faiss.Index, evidence_list: List[Dict[str, Any]]):
        """
        Save FAISS index and metadata to disk
        Args:
            index: FAISS index object
            evidence_list: List of evidence objects
        """
        # Save FAISS index
        faiss.write_index(index, self.faiss_index_path)
        self.logger.info(f"FAISS index saved to: {self.faiss_index_path}")
        
        # Prepare metadata
        metadata = {
            'evidence_count': len(evidence_list),
            'embedding_model': self.embedding_model,
            'embedding_dimension': self.embedding_dimension,
            'type_weights': self.type_weights,
            'evidence_list': evidence_list  # Save complete evidence information
        }
        
        # Save metadata
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        self.logger.info(f"Metadata saved to: {self.metadata_path}")
    
    def process_all(self):
        """
        Execute complete embedding preprocessing pipeline
        """
        self.logger.info("Starting embedding preprocessing...")
        
        # 1. Create output directory
        self.create_output_directory()
        
        # 2. Load data
        evidence_list = self.load_evidence_data()
        
        # 3. Prepare texts
        self.logger.info("Preparing texts for embedding...")
        texts = [self.prepare_text_for_embedding(evidence) for evidence in evidence_list]
        
        # 4. Generate embeddings
        self.logger.info("Generating embeddings...")
        embeddings = self.get_embeddings_batch(texts)
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # 5. Create FAISS index (without applying weights to embeddings)
        index = self.create_faiss_index(embeddings_array)
        
        # 6. Save results
        self.save_index_and_metadata(index, evidence_list)
        
        self.logger.info("Embedding preprocessing completed successfully!")
        
        # Print statistics
        self.print_statistics(evidence_list)
    
    def print_statistics(self, evidence_list: List[Dict[str, Any]]):
        """Print processing statistics"""
        self.logger.info("\n=== Processing Statistics ===")
        self.logger.info(f"Total evidence count: {len(evidence_list)}")
        
        # Count by type
        type_counts = {}
        for evidence in evidence_list:
            category = evidence.get('category', 'unknown')
            type_counts[category] = type_counts.get(category, 0) + 1
        
        self.logger.info("Distribution by type:")
        for category, count in sorted(type_counts.items()):
            weight = self.type_weights.get(category, 1.0)
            self.logger.info(f"  {category}: {count} items (weight: {weight})")


def main():
    """Main function for embedding preprocessing"""
    try:
        # Create processor and execute
        processor = EvidenceEmbeddingProcessor()
        processor.process_all()
    except Exception as e:
        logging.error(f"Embedding preprocessing failed: {str(e)}")
        raise


if __name__ == "__main__":
    main() 