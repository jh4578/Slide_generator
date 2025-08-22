"""
Image Generation Chain for FRESCO study presentations
Analyzes evidence images using GPT-4 Vision and generates new images when appropriate
"""

from typing import List, Dict, Any, Optional
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema import BaseOutputParser
import json
import os
import logging
import base64
from PIL import Image
import requests

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

logger = logging.getLogger(__name__)

class ImageAnalysisOutputParser(BaseOutputParser):
    """Parser for image analysis output"""
    
    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse LLM output into structured image analysis
        Args:
            text: Raw LLM output
        Returns:
            Dictionary with parsed analysis
        """
        try:
            # Try to parse as JSON first
            if text.strip().startswith('{'):
                parsed = json.loads(text)
                return parsed
            
            # Fallback: treat as text analysis
            return {
                "has_relevant_features": False,
                "analysis": text,
                "chart_type": "unknown",
                "key_findings": [],
                "generation_needed": False
            }
            
        except Exception as e:
            logger.error(f"Failed to parse image analysis output: {e}")
            return {
                "has_relevant_features": False,
                "analysis": f"Analysis failed: {str(e)}",
                "chart_type": "unknown", 
                "key_findings": [],
                "generation_needed": False
            }

class ImageGeneratorChain:
    """
    LangChain component for analyzing and generating images for medical presentations
    Uses GPT-4 Vision to analyze evidence images and decides when to generate new ones
    """
    
    def __init__(self):
        """Initialize the image generator with Vision API and templates"""
        # Setup logging
        config.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Get OpenAI configuration
        openai_config = config.get_openai_config()
        
        # Initialize Vision LLM (GPT-4o for analyzing images)
        self.vision_llm = ChatOpenAI(
            model=config.vision_model,
            temperature=config.vision_temperature,
            api_key=openai_config['api_key'],
            max_tokens=config.vision_max_tokens
        )
        
        # Initialize Image Generation LLM (GPT Image 1 for generating images)
        self.image_gen_llm = ChatOpenAI(
            model=config.image_model,
            temperature=0.3,
            api_key=openai_config['api_key']
        )
        
        # Paths
        self.templates_dir = os.path.join(config.project_root, 'templates')
        self.evidence_images_dir = os.path.join(config.project_root, 'preprocessing', 'images')
        self.output_images_dir = os.path.join(config.html_generator_root, 'output', 'generated_images')
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_images_dir, exist_ok=True)
        
        # Create prompt template for image analysis
        self.analysis_prompt = self._create_analysis_prompt()
        
        # Create the analysis chain
        self.analysis_chain = LLMChain(
            llm=self.vision_llm,
            prompt=self.analysis_prompt,
            output_parser=ImageAnalysisOutputParser()
        )
        
        self.logger.info("ImageGeneratorChain initialized successfully")
    
    def _create_analysis_prompt(self) -> PromptTemplate:
        """
        Create prompt template for image analysis
        Returns:
            PromptTemplate configured for medical image analysis
        """
        template = """
You are a medical data visualization expert analyzing images from clinical studies about fruquintinib in metastatic colorectal cancer.

Analyze the provided image and determine:
1. Does this image contain clinically relevant data (charts, graphs, tables with data)?
2. What type of medical data visualization is this?
3. What are the key clinical findings shown?
4. Would generating a similar chart be valuable for a medical presentation?

User Query Context: "{user_query}"

Provide your analysis in the following JSON format:
{{
    "has_relevant_features": true/false,
    "chart_type": "kaplan_meier/bar_chart/line_graph/table/forest_plot/other",
    "clinical_data_type": "survival/efficacy/safety/demographics/other",
    "key_findings": ["list", "of", "key", "findings"],
    "data_elements": {{
        "primary_endpoint": "description",
        "sample_size": "if visible",
        "statistical_significance": "if shown"
    }},
    "generation_needed": true/false,
    "generation_rationale": "explanation of why generation is/isn't needed",
    "template_match": "efficacy_os/safety/other/none"
}}

Only recommend generation_needed=true if:
- The image shows clear clinical data that could be recreated
- The data type matches the user's query intent
- The visualization would add significant value to a medical presentation

Image to analyze: [IMAGE_DATA]
"""
        
        return PromptTemplate(
            input_variables=["user_query"],
            template=template
        )
    
    def _encode_image(self, image_path: str) -> str:
        """
        Encode image to base64 for Vision API
        Args:
            image_path: Path to image file
        Returns:
            Base64 encoded image string
        """
        try:
            full_path = os.path.join(self.evidence_images_dir, image_path)
            if not os.path.exists(full_path):
                self.logger.warning(f"Image not found: {full_path}")
                return None
                
            with open(full_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Failed to encode image {image_path}: {e}")
            return None
    
    def _extract_image_evidences(self, evidence_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract image type evidences from search results
        Args:
            evidence_results: List of all evidence items
        Returns:
            List of image evidence items
        """
        image_evidences = []
        for evidence in evidence_results:
            if evidence.get('type') == 'image':
                image_evidences.append(evidence)
        
        self.logger.info(f"Found {len(image_evidences)} image evidences")
        return image_evidences
    
    def _analyze_single_image(self, user_query: str, image_evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single image using Vision API
        Args:
            user_query: User's original query
            image_evidence: Image evidence item
        Returns:
            Analysis results
        """
        # Get image path from original_content field, not content field
        image_path = image_evidence.get('original_content', '')
        if image_path.startswith('images/'):
            image_path = image_path[7:]  # Remove 'images/' prefix
        
        # Encode image
        encoded_image = self._encode_image(image_path)
        if not encoded_image:
            return {
                "has_relevant_features": False,
                "analysis": "Could not load image",
                "generation_needed": False
            }
        
        try:
            # Prepare the message with image for Vision API
            if not encoded_image:
                raise Exception("No image data available for analysis")
            
            # Create vision message with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""You are a medical data visualization expert analyzing images from clinical studies about fruquintinib in metastatic colorectal cancer.

Analyze the provided image and determine:
1. Does this image contain clinically relevant data (charts, graphs, tables with data)?
2. What type of medical data visualization is this?
3. What are the key clinical findings shown?
4. Would generating a similar chart be valuable for a medical presentation?

User Query Context: "{user_query}"

Provide your analysis in the following JSON format:
{{
    "has_relevant_features": true/false,
    "chart_type": "kaplan_meier/bar_chart/line_graph/table/forest_plot/other",
    "clinical_data_type": "survival/efficacy/safety/demographics/other",
    "key_findings": ["list", "of", "key", "findings"],
    "data_elements": {{
        "primary_endpoint": "description",
        "sample_size": "if visible",
        "statistical_significance": "if shown"
    }},
    "generation_needed": true/false,
    "generation_rationale": "explanation of why generation is/isn't needed",
    "template_match": "efficacy_os/safety/other/none"
}}

Only recommend generation_needed=true if:
- The image shows clear clinical data that could be recreated
- The data type matches the user's query intent
- The visualization would add significant value to a medical presentation"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{encoded_image}"
                            }
                        }
                    ]
                }
            ]
            
            # Call vision model directly
            result = self.vision_llm.invoke(messages)
            
            # Parse the result
            if hasattr(result, 'content'):
                result_text = result.content
            else:
                result_text = str(result)
            
            # Try to parse as JSON
            try:
                import json
                parsed_result = json.loads(result_text)
            except:
                # Fallback parsing
                parsed_result = {
                    "has_relevant_features": "kaplan-meier" in result_text.lower() or "survival" in result_text.lower(),
                    "chart_type": "kaplan_meier" if "kaplan-meier" in result_text.lower() else "unknown",
                    "clinical_data_type": "survival" if "survival" in result_text.lower() else "unknown",
                    "key_findings": [result_text[:100]],
                    "generation_needed": False,
                    "analysis": result_text
                }
            
            result = parsed_result
            
            # Add image metadata
            result['evidence_id'] = image_evidence.get('id')
            result['image_path'] = image_path
            result['source_document'] = image_evidence.get('source_document')
            result['page_number'] = image_evidence.get('page_number')
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to analyze image {image_path}: {e}")
            return {
                "has_relevant_features": False,
                "analysis": f"Analysis failed: {str(e)}",
                "generation_needed": False,
                "evidence_id": image_evidence.get('id'),
                "image_path": image_path
            }
    
    def _select_template_image(self, user_query: str, analyses: List[Dict[str, Any]]) -> Optional[str]:
        """
        Select appropriate template image based on query and analysis
        Args:
            user_query: User's query
            analyses: List of image analyses
        Returns:
            Path to template image or None
        """
        query_lower = user_query.lower()
        
        # Check for template matches in analyses
        for analysis in analyses:
            template_match = analysis.get('template_match', 'none')
            if template_match != 'none':
                template_path = os.path.join(self.templates_dir, f"{template_match}.png")
                if os.path.exists(template_path):
                    self.logger.info(f"Selected template: {template_match}.png")
                    return template_path
        
        # Fallback query-based matching
        if any(term in query_lower for term in ['efficacy', 'os', 'overall survival']):
            template_path = os.path.join(self.templates_dir, 'efficacy_os.png')
            if os.path.exists(template_path):
                return template_path
        
        return None
    
    def _should_generate_images(self, analyses: List[Dict[str, Any]]) -> bool:
        """
        Determine if image generation is needed based on analyses
        Args:
            analyses: List of image analyses
        Returns:
            True if there are any relevant images to work with
        """
        # ALWAYS generate if we have relevant clinical images
        for analysis in analyses:
            if analysis.get('has_relevant_features', False):
                return True
        return False
    
    def _create_generation_prompt(self, user_query: str, analysis: Dict[str, Any], template_path: Optional[str] = None) -> str:
        """
        Create detailed prompt for image generation based on analysis and template
        Args:
            user_query: Original user query
            analysis: Image analysis results
            template_path: Path to template image
        Returns:
            Detailed generation prompt
        """
        # Extract key information from analysis
        chart_type = analysis.get('chart_type', 'clinical_chart')
        clinical_data = analysis.get('clinical_data_type', 'medical_data')
        key_findings = analysis.get('key_findings', [])
        
        # Get template style description
        template_style = ""
        if template_path and os.path.exists(template_path):
            template_name = os.path.basename(template_path)
            template_style = f"Use the visual style and layout from {template_name} as reference. "
        
        # Create comprehensive prompt
        prompt = f"""Create a professional medical data visualization chart for a pharmaceutical presentation about fruquintinib in metastatic colorectal cancer.

ORIGINAL IMAGE ANALYSIS:
- Chart Type: {chart_type}
- Clinical Data: {clinical_data}
- Key Findings: {', '.join(key_findings) if key_findings else 'Clinical survival data'}

GENERATION REQUIREMENTS:
- Recreate a similar {chart_type} chart using the same data pattern
- Focus on {clinical_data} outcomes for fruquintinib
- {template_style}
- Use professional medical chart styling
- Include clear axis labels, legends, and statistical annotations
- Use pharmaceutical branding colors (blues, purples, medical greens)
- Ensure readability for medical presentations
- Include confidence intervals and p-values where appropriate

STYLE SPECIFICATIONS:
- Clean, professional medical chart appearance
- White/light background suitable for presentations  
- High contrast text and data points
- Professional typography
- Clear data visualization best practices

Query Context: {user_query}

Generate a high-quality clinical data visualization that medical professionals would use in presentations."""

        return prompt
    
    def _get_original_image_path(self) -> Optional[str]:
        """
        Get the path to the original image being processed
        Returns:
            Path to original image file
        """
        # This will be set during processing
        return getattr(self, '_current_original_image_path', None)
    
    def _generate_image_with_gpt_image_1(self, prompt: str, template_path: Optional[str] = None) -> Optional[str]:
        """
        Generate image using GPT Image 1
        Args:
            prompt: Text prompt for image generation
            template_path: Optional template image path for style reference
        Returns:
            Path to generated image or None
        """
        try:
            # Use GPT Image 1 edit API (image-to-image with template)
            self.logger.info("Generating image with GPT Image 1 edit API...")
            self.logger.info(f"Generation prompt: {prompt[:200]}...")
            
            # Use OpenAI's image edit API with original image and template
            from openai import OpenAI
            openai_config = config.get_openai_config()
            client = OpenAI(api_key=openai_config['api_key'])
            
            # Prepare image inputs
            image_files = []
            
            # Add original image (from evidence)
            original_image_path = self._get_original_image_path()
            if original_image_path and os.path.exists(original_image_path):
                image_files.append(open(original_image_path, "rb"))
                self.logger.info(f"Added original image: {original_image_path}")
            
            # Add template image if available
            if template_path and os.path.exists(template_path):
                image_files.append(open(template_path, "rb"))
                self.logger.info(f"Added template image: {template_path}")
            
            if not image_files:
                raise Exception("No images available for generation")
            
            try:
                # Call GPT Image 1 edit API
                response = client.images.edit(
                    model="gpt-image-1",
                    image=image_files,  # Array of file objects: [original, template]
                    prompt=prompt,
                    size="1024x1024",
                    n=1,
                )
            finally:
                # Close file handles
                for f in image_files:
                    f.close()
            
            # Process the response and download the image
            self.logger.info(f"API Response: {response}")
            
            if response and response.data:
                # Check different possible response formats
                image_data = response.data[0]
                self.logger.info(f"Image data: {image_data}")
                
                # Try different ways to get the image
                image_url = None
                if hasattr(image_data, 'url') and image_data.url:
                    image_url = image_data.url
                elif hasattr(image_data, 'b64_json') and image_data.b64_json:
                    # Handle base64 response
                    import uuid
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    unique_id = str(uuid.uuid4())[:8]
                    filename = f"generated_chart_{timestamp}_{unique_id}.png"
                    output_path = os.path.join(self.output_images_dir, filename)
                    
                    # Decode and save base64 image
                    image_bytes = base64.b64decode(image_data.b64_json)
                    with open(output_path, 'wb') as f:
                        f.write(image_bytes)
                    
                    self.logger.info(f"Image saved from base64: {filename}")
                    return f"generated_images/{filename}"
                
                if not image_url:
                    self.logger.error("No image URL or base64 data found in response")
                    return None
                
                revised_prompt = getattr(image_data, 'revised_prompt', prompt)
                
                # Generate unique filename
                import uuid
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_id = str(uuid.uuid4())[:8]
                filename = f"generated_chart_{timestamp}_{unique_id}.png"
                output_path = os.path.join(self.output_images_dir, filename)
                
                # Download and save the image
                try:
                    import requests
                    img_response = requests.get(image_url)
                    img_response.raise_for_status()
                    
                    with open(output_path, 'wb') as f:
                        f.write(img_response.content)
                    
                    # Also save metadata
                    with open(output_path.replace('.png', '_info.txt'), 'w') as f:
                        f.write(f"Generated image metadata\n")
                        f.write(f"Original prompt: {prompt}\n")
                        f.write(f"Revised prompt: {revised_prompt}\n")
                        f.write(f"Image URL: {image_url}\n")
                        f.write(f"Timestamp: {timestamp}\n")
                    
                    self.logger.info(f"Image generation completed: {filename}")
                    self.logger.info(f"Image saved at: {output_path}")
                    
                    # Return the relative path for HTML
                    return f"generated_images/{filename}"
                    
                except Exception as save_error:
                    self.logger.error(f"Failed to download and save image: {save_error}")
                    return None
            else:
                self.logger.error("No image data received from API")
                return None
            
        except Exception as e:
            self.logger.error(f"Failed to generate image with GPT Image 1: {e}")
            return None
    
    def _create_html_image_references(self, analyses: List[Dict[str, Any]], 
                                    generated_images: List[str] = None) -> List[str]:
        """
        Create HTML references for processed images
        Args:
            analyses: Image analyses
            generated_images: List of generated image paths
        Returns:
            List of HTML code snippets for images
        """
        html_refs = []
        
        # Add existing evidence images that are relevant
        for analysis in analyses:
            if analysis.get('has_relevant_features', False):
                image_path = analysis.get('image_path', '')
                html_ref = f"""
                <div class="evidence-image">
                    <img src="../../preprocessing/images/{image_path}" 
                         alt="{analysis.get('chart_type', 'Clinical chart')}" 
                         class="clinical-chart">
                    <p class="image-caption">
                        {analysis.get('clinical_data_type', 'Clinical data')}: 
                        {', '.join(analysis.get('key_findings', [])[:2])}
                    </p>
                </div>
                """
                html_refs.append(html_ref)
        
        # Add generated images (prioritize these)
        if generated_images:
            for img_path in generated_images:
                html_ref = f"""
                <div class="generated-image">
                    <img src="../html_generator/output/{img_path}" 
                         alt="Generated clinical visualization based on original data" 
                         class="generated-chart">
                    <p class="image-caption">
                        <strong>Generated Clinical Chart:</strong> Created using original study data and professional medical visualization standards.
                    </p>
                </div>
                """
                html_refs.append(html_ref)
        
        return html_refs
    
    def process_images(self, user_query: str, evidence_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Main method to process images for a given query and evidence
        Args:
            user_query: User's original query
            evidence_results: List of all evidence items from semantic search
        Returns:
            Dictionary with image processing results
        """
        self.logger.info(f"Processing images for query: {user_query}")
        
        # Step 1: Extract image evidences
        image_evidences = self._extract_image_evidences(evidence_results)
        self.logger.info(f"Found {len(image_evidences)} image evidences")
        
        if not image_evidences:
            self.logger.info("No image evidences found, skipping image processing")
            return {
                'has_images': False,
                'should_generate': False,
                'image_count': 0,
                'selected_image_path': None,
                'html_image_references': [],
                'background_image': 'bg.png'  # Always include background
            }
        
        # Step 2: Select the image with highest similarity score
        best_image = max(image_evidences, key=lambda x: x.get('similarity_score', 0))
        best_similarity = best_image.get('similarity_score', 0)
        
        self.logger.info(f"Selected best image with similarity score: {best_similarity:.3f}")
        self.logger.info(f"Best image ID: {best_image.get('id')}")
        self.logger.info(f"Best image source: {best_image.get('source_document')}")
        
        # Extract image path from original_content
        image_path = best_image.get('original_content', '')
        if image_path.startswith('images/'):
            image_path = image_path[7:]  # Remove 'images/' prefix
        
        # Construct the full path for the selected image
        full_image_path = os.path.join(self.evidence_images_dir, image_path)
        
        # Check if image exists
        if not os.path.exists(full_image_path):
            self.logger.warning(f"Selected image not found: {full_image_path}")
            return {
                'has_images': False,
                'should_generate': False,
                'image_count': 0,
                'selected_image_path': None,
                'html_image_references': [],
                'background_image': 'bg.png'
            }
        
        # Create the relative path for HTML generation
        # The path should be relative to the HTML file location
        relative_image_path = f"../../preprocessing/images/{image_path}"
        
        self.logger.info(f"Selected image path: {relative_image_path}")
        
        return {
            'has_images': True,
            'should_generate': False,  # Skip generation, use existing image
            'image_count': 1,
            'selected_image_path': relative_image_path,
            'selected_image_info': {
                'id': best_image.get('id'),
                'source_document': best_image.get('source_document'),
                'page_number': best_image.get('page_number'),
                'similarity_score': best_similarity,
                'content': best_image.get('content', ''),
                'category': best_image.get('category', '')
            },
            'html_image_references': [],  # Will be handled by HTML generator
            'background_image': 'bg.png'
        } 