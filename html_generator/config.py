"""
Configuration module for HTML generator
Handles environment variables and project settings
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    """Configuration class for HTML generator module"""
    
    def __init__(self):
        """Initialize configuration with environment variables and defaults"""
        
        # OpenAI Configuration
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Embedding Configuration
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-large')
        self.embedding_dimension = int(os.getenv('EMBEDDING_DIMENSION', '3072'))
        self.embedding_batch_size = int(os.getenv('EMBEDDING_BATCH_SIZE', '100'))
        
        # LLM Configuration
        self.llm_model = os.getenv('LLM_MODEL', 'gpt-4-turbo-preview')
        self.llm_temperature = float(os.getenv('LLM_TEMPERATURE', '0.3'))
        self.max_tokens = int(os.getenv('MAX_TOKENS', '4000'))
        
        # Vision API Configuration
        self.vision_model = os.getenv('VISION_MODEL', 'gpt-4o')
        self.vision_temperature = float(os.getenv('VISION_TEMPERATURE', '0.1'))
        self.vision_max_tokens = int(os.getenv('VISION_MAX_TOKENS', '2000'))
        
        # Image Generation Configuration  
        
        self.image_model = os.getenv('IMAGE_MODEL', 'gpt-image-1')
        self.image_quality = os.getenv('IMAGE_QUALITY', 'standard')  # standard or hd
        self.image_size = os.getenv('IMAGE_SIZE', '1024x1024')  # 1024x1024, 1792x1024, or 1024x1792
        
        # File Paths (relative to project root)
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.extracted_content_path = os.path.join(
            self.project_root, 
            'preprocessing', 
            'extracted_content.json'
        )
        # Template paths for different content types
        self.templates_dir = os.path.join(self.project_root, 'templates')
        self.template_paths = {
            'image': os.path.join(self.templates_dir, 'templates_image1.html'),
            'table': os.path.join(self.templates_dir, 'templates_table1.html'), 
            'text': os.path.join(self.templates_dir, 'templates_text1.html'),
            'default': os.path.join(self.templates_dir, 'templates.html')
        }
        
        # Image Paths
        self.templates_dir = os.path.join(self.project_root, 'templates')
        self.evidence_images_dir = os.path.join(self.project_root, 'preprocessing', 'images')
        
        # HTML Generator Paths
        self.html_generator_root = os.path.join(self.project_root, 'html_generator')
        self.embeddings_dir = os.path.join(self.html_generator_root, 'embeddings')
        self.faiss_index_path = os.path.join(self.embeddings_dir, 'evidence_embeddings.faiss')
        self.metadata_path = os.path.join(self.embeddings_dir, 'evidence_metadata.pkl')
        
        # Output directories
        self.output_dir = os.path.join(self.html_generator_root, 'output')
        self.generated_images_dir = os.path.join(self.output_dir, 'generated_images')
        
        # Evidence Type Weights
        self.type_weights = {
            "extracted_image": float(os.getenv('WEIGHT_IMAGE', '1.5')),
            "table": float(os.getenv('WEIGHT_TABLE', '1.3')),
            "figure": float(os.getenv('WEIGHT_FIGURE', '1.4')),
            "chart": float(os.getenv('WEIGHT_CHART', '1.4')),
            "text": float(os.getenv('WEIGHT_TEXT', '1.0')),
            "general": float(os.getenv('WEIGHT_GENERAL', '1.0'))
        }
        
        # Search Configuration
        self.top_k_results = int(os.getenv('TOP_K_RESULTS', '20'))
        self.similarity_threshold = float(os.getenv('SIMILARITY_THRESHOLD', '0.5'))
        self.query_expansion_count = int(os.getenv('QUERY_EXPANSION_COUNT', '3'))
        
        # Multi-page Configuration
        self.max_concurrent_pages = int(os.getenv('MAX_CONCURRENT_PAGES', '3'))
        self.enable_multi_page = os.getenv('ENABLE_MULTI_PAGE', 'true').lower() == 'true'
        self.auto_page_detection = os.getenv('AUTO_PAGE_DETECTION', 'true').lower() == 'true'
        self.max_pages_per_presentation = int(os.getenv('MAX_PAGES_PER_PRESENTATION', '10'))
        
        # Image Processing Configuration
        self.image_analysis_threshold = float(os.getenv('IMAGE_ANALYSIS_THRESHOLD', '0.7'))
        self.enable_image_generation = os.getenv('ENABLE_IMAGE_GENERATION', 'true').lower() == 'true'
        self.max_images_per_query = int(os.getenv('MAX_IMAGES_PER_QUERY', '3'))
        
        # Logging Configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_format = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Validate paths
        self._validate_paths()
        
        logger.info("Configuration initialized successfully")
    
    def _validate_paths(self):
        """Validate that required files and directories exist"""
        if not os.path.exists(self.extracted_content_path):
            raise FileNotFoundError(f"Extracted content file not found: {self.extracted_content_path}")
        
        # Validate all template files exist
        for template_type, template_path in self.template_paths.items():
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"Template file not found: {template_path} (type: {template_type})")
        
        # Create required directories if they don't exist
        os.makedirs(self.embeddings_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.generated_images_dir, exist_ok=True)
    
    def get_openai_config(self) -> Dict[str, Any]:
        """Get OpenAI configuration dictionary"""
        return {
            'api_key': self.openai_api_key,
            'embedding_model': self.embedding_model,
            'llm_model': self.llm_model,
            'temperature': self.llm_temperature,
            'max_tokens': self.max_tokens
        }
    
    def get_vision_config(self) -> Dict[str, Any]:
        """Get Vision API configuration dictionary"""
        return {
            'api_key': self.openai_api_key,
            'model': self.vision_model,
            'temperature': self.vision_temperature,
            'max_tokens': self.vision_max_tokens
        }
    
    def get_image_generation_config(self) -> Dict[str, Any]:
        """Get GPT Image 1 configuration dictionary"""
        return {
            'api_key': self.openai_api_key,
            'model': self.image_model,
            'quality': self.image_quality,
            'size': self.image_size
        }
    
    def get_image_config(self) -> Dict[str, Any]:
        """Get image processing configuration dictionary"""
        return {
            'analysis_threshold': self.image_analysis_threshold,
            'enable_generation': self.enable_image_generation,
            'max_images': self.max_images_per_query,
            'templates_dir': self.templates_dir,
            'evidence_images_dir': self.evidence_images_dir,
            'output_dir': self.generated_images_dir
        }
    
    def get_embedding_config(self) -> Dict[str, Any]:
        """Get embedding configuration dictionary"""
        return {
            'model': self.embedding_model,
            'dimension': self.embedding_dimension,
            'batch_size': self.embedding_batch_size,
            'type_weights': self.type_weights
        }
    
    def get_search_config(self) -> Dict[str, Any]:
        """Get search configuration dictionary"""
        return {
            'top_k': self.top_k_results,
            'threshold': self.similarity_threshold,
            'expansion_count': self.query_expansion_count
        }
    
    def get_multi_page_config(self) -> Dict[str, Any]:
        """Get multi-page configuration dictionary"""
        return {
            'max_concurrent_pages': self.max_concurrent_pages,
            'enable_multi_page': self.enable_multi_page,
            'auto_page_detection': self.auto_page_detection,
            'max_pages_per_presentation': self.max_pages_per_presentation
        }
    
    def get(self, key: str, default=None):
        """Get configuration value by key with optional default"""
        return getattr(self, key, default)
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format=self.log_format
        )

# Global configuration instance
config = Config() 