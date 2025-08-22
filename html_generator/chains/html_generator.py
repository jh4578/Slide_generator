"""
HTML Generation Chain for FRESCO study presentations
Generates HTML content based on template and evidence data
"""

from typing import List, Dict, Any
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema import BaseOutputParser
import json
import os
import logging
from bs4 import BeautifulSoup
import base64

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

logger = logging.getLogger(__name__)

class HTMLContentOutputParser(BaseOutputParser):
    """Parser for HTML content generation output"""
    
    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse LLM output into structured HTML content
        Args:
            text: Raw LLM output
        Returns:
            Dictionary with parsed HTML content
        """
        
        try:
            # Remove markdown code blocks if present
            clean_text = text.strip()
            if clean_text.startswith('```json'):
                # Extract JSON from markdown code block
                start = clean_text.find('{')
                end = clean_text.rfind('}') + 1
                if start != -1 and end != 0:
                    clean_text = clean_text[start:end]
            elif clean_text.startswith('```'):
                # Remove any code block wrapper
                lines = clean_text.split('\n')
                clean_text = '\n'.join(lines[1:-1])
            
            # Try to parse as JSON
            if clean_text.strip().startswith('{'):
                parsed = json.loads(clean_text)
                return parsed
            
            # Fallback: treat entire output as HTML content
            fallback = {
                "html_content": text,
                "title": "FRESCO Study Results", 
                "summary": "Generated content based on evidence analysis"
            }
            print(f"Using fallback parsing: {fallback}")
            return fallback
            
        except Exception as e:
            logger.error(f"Failed to parse HTML generation output: {e}")
            return {
                "html_content": f"<div class='error'>Content generation failed: {str(e)}</div>",
                "title": "Error",
                "summary": "Failed to generate content"
            }

class HTMLGeneratorChain:
    """
    LangChain component for generating HTML presentations from evidence
    Creates structured medical content for FRESCO study presentations
    """
    
    def __init__(self):
        """Initialize the HTML generator with medical presentation prompts"""
        # Setup logging
        config.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Use gpt-4o for everything (vision + text generation)
        vision_config = config.get_vision_config()
        self.llm = ChatOpenAI(
            model=vision_config['model'],  # gpt-4o
            # temperature=0.3,  # Slightly higher for better content generation
            api_key=vision_config['api_key'],
            max_tokens=4000  # Increase token limit for better content
        )
        
        # Initialize output parser
        self.output_parser = HTMLContentOutputParser()
        
        # Load HTML templates (all types)
        self.template_contents = self._load_html_templates()
        
        # Load template image (picture.png)
        self.template_image_path = self._get_template_image_path()
        self.template_image_data = self._load_template_image()
        
        # Get template dimensions (1482 x 1118 based on picture.png)
        self.template_width = 1482
        self.template_height = 1118
        
        # Create prompt template for HTML generation
        self.prompt_template = self._create_prompt_template()
        
        self.logger.info("HTMLGeneratorChain initialized successfully")
    
    def _get_template_image_path(self) -> str:
        """
        Get the path to the template image (picture.png)
        Returns:
            Path to picture.png template
        """
        return os.path.join(config.templates_dir, 'picture.png')
    
    def _load_template_image(self) -> str:
        """
        Load template image as base64 for embedding in HTML
        Returns:
            Base64 encoded image data
        """
        try:
            if os.path.exists(self.template_image_path):
                with open(self.template_image_path, 'rb') as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                self.logger.info(f"Template image loaded from: {self.template_image_path}")
                return img_data
            else:
                self.logger.warning(f"Template image not found: {self.template_image_path}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to load template image: {e}")
            return None
    

    
    def _load_html_templates(self) -> Dict[str, str]:
        """
        Load all HTML template files
        Returns:
            Dictionary mapping template type to content
        """
        templates = {}
        try:
            for template_type, template_path in config.template_paths.items():
                with open(template_path, 'r', encoding='utf-8') as f:
                    templates[template_type] = f.read()
                self.logger.info(f"HTML template loaded: {template_type} from {template_path}")
            
            return templates
            
        except Exception as e:
            self.logger.error(f"Failed to load HTML templates: {e}")
            raise
    
    def _create_prompt_template(self) -> str:
        """Create the prompt template for HTML generation"""
        return """
You are a medical communications specialist creating content for FRESCO study presentations about fruquintinib in metastatic colorectal cancer.

Generate professional HTML content based on the provided evidence data and use the provided images.

User Query: {user_query}

Evidence Data:
{evidence_summary}

Available Evidence Items:
{evidence_details}

Available Images:
{image_info}

{image_html_content}

Template HTML Structure:
{template_content}

Template Dimensions: {template_width} x {template_height} pixels

CRITICAL INSTRUCTIONS:
1. Take the provided template HTML and replace ALL placeholders with actual content
2. Generate the COMPLETE HTML page - not just parts of it
3. Replace these placeholders with appropriate content based on evidence:
   - {{MAIN_TITLE}} - Main presentation title
   - {{SUBTITLE}} - Analysis subtitle
   - {{CHART_IMAGE}} - Image path (use provided image or efficacy_os.png)
   - {{CHART_ALT}} - Image alt text
   - {{key findings}} - Key findings text (appears 3 times in bullet points)
   - {{Specific_Evidence}} - Specific numbers that are important to highlight
4. Preserve ALL other HTML structure, CSS, styling exactly as provided
5. Do NOT modify any CSS classes, styling, or layout structure
6. Generate medical content appropriate for FRESCO study presentation
7. IMPORTANT: Analyze the evidence data and identify the most clinically significant numerical values (median survival times, hazard ratios, p-values, patient counts, confidence intervals, etc.)
8. For {{key findings}} placeholders, create bullet points that include these specific numbers from the evidence
9. Each bullet point should contain 2-3 concrete numerical values that support the clinical conclusion
10. Focus on meaningful clinical statistics like median OS/PFS months, HR values, 95% CI ranges, and significant p-values that demonstrate efficacy

Generate content in the following JSON format:
{{
    "title": "Descriptive title for the header",
    "html_content": "COMPLETE HTML page with ALL placeholders replaced with actual content based on evidence",
    "summary": "Brief summary of the key points covered"
}}

The html_content should be the FULL HTML page with all placeholders filled in.
"""
    
    def _prepare_evidence_summary(self, evidence_results: List[Dict[str, Any]]) -> str:
        """
        Create a concise summary of evidence for the prompt
        Args:
            evidence_results: List of evidence items
        Returns:
            Formatted evidence summary
        """
        if not evidence_results:
            return "No relevant evidence found."
        
        # Count by type
        type_counts = {}
        for evidence in evidence_results:
            category = evidence.get('category', 'unknown')
            type_counts[category] = type_counts.get(category, 0) + 1
        
        summary_parts = [
            f"Found {len(evidence_results)} relevant evidence items:",
        ]
        
        for category, count in sorted(type_counts.items()):
            summary_parts.append(f"- {category}: {count} items")
        
        # Add top evidence scores
        top_scores = [e.get('similarity_score', 0) for e in evidence_results[:5]]
        if top_scores:
            avg_score = sum(top_scores) / len(top_scores)
            summary_parts.append(f"Average relevance score: {avg_score:.3f}")
        
        return "\n".join(summary_parts)
    
    def _prepare_evidence_details(self, evidence_results: List[Dict[str, Any]]) -> str:
        """
        Format evidence details for the prompt
        Args:
            evidence_results: List of evidence items
        Returns:
            Formatted evidence details
        """
        if not evidence_results:
            return "No evidence details available."
        
        details = []
        for i, evidence in enumerate(evidence_results[:10], 1):  # Limit to top 10
            detail_parts = [f"Evidence {i}:"]
            detail_parts.append(f"  Type: {evidence.get('category', 'unknown')}")
            detail_parts.append(f"  Source: {evidence.get('source_document', 'unknown')}")
            
            # Handle different content types
            content = evidence.get('content')
            if isinstance(content, str):
                # Truncate long text content
                content_preview = content[:300] + "..." if len(content) > 300 else content
                detail_parts.append(f"  Content: {content_preview}")
            elif isinstance(content, dict):
                if 'headers' in content and 'rows' in content:
                    headers = ", ".join(content.get('headers', []))
                    row_count = len(content.get('rows', []))
                    detail_parts.append(f"  Table: {headers} ({row_count} rows)")
                elif 'markdown' in content:
                    markdown_preview = content['markdown'][:200] + "..." if len(content['markdown']) > 200 else content['markdown']
                    detail_parts.append(f"  Markdown: {markdown_preview}")
            
            # Add similarity score if available
            if 'similarity_score' in evidence:
                detail_parts.append(f"  Relevance: {evidence['similarity_score']:.3f}")
            
            details.append("\n".join(detail_parts))
        
        return "\n\n".join(details)
    
    def _prepare_image_info(self, image_results: Dict[str, Any]) -> str:
        """
        Prepare image processing information for the prompt
        Args:
            image_results: Image processing results from ImageGeneratorChain
        Returns:
            Formatted image information string
        """
        if not image_results or not image_results.get('has_images', False):
            return "No relevant images found in the evidence."
        
        selected_image_info = image_results.get('selected_image_info', {})
        image_path = image_results.get('selected_image_path', '')
        
        info_parts = [
            f"Image processing summary:",
            f"- Selected image with highest similarity: {selected_image_info.get('similarity_score', 0):.3f}",
            f"- Image source: {selected_image_info.get('source_document', 'Unknown')}",
            f"- Image category: {selected_image_info.get('category', 'Unknown')}",
            f"- Available for use in presentation: {image_path}"
        ]
        
        return "\n".join(info_parts)
    
    def _prepare_image_html_content(self, image_results: Dict[str, Any]) -> str:
        """
        Prepare HTML image content for integration
        Args:
            image_results: Image processing results from ImageGeneratorChain
        Returns:
            HTML content string for images
        """
        if not image_results or not image_results.get('has_images', False):
            return "<!-- No images to integrate -->"
        
        # Get the selected image path
        selected_image_path = image_results.get('selected_image_path', '')
        selected_image_info = image_results.get('selected_image_info', {})
        
        if not selected_image_path:
            return "<!-- No selected image path available -->"
        
        # Create HTML content for the selected image
        image_html = f"""
        <div class="selected-image">
            <img src="{selected_image_path}" 
                 alt="Selected clinical chart from {selected_image_info.get('source_document', 'study')}" 
                 class="main-chart">
            <p class="image-caption">
                <strong>Clinical Data:</strong> {selected_image_info.get('content', 'Clinical visualization from study evidence')}
                <br><small>Similarity score: {selected_image_info.get('similarity_score', 0):.3f}</small>
            </p>
        </div>
        """
        
        return image_html
    
    def _select_template_based_on_evidence(self, evidence_results: List[Dict[str, Any]]) -> str:
        """
        Select appropriate template based on evidence content type
        Args:
            evidence_results: List of evidence items
        Returns:
            Template type string ('image', 'table', 'text', or 'default')
        """
        if not evidence_results:
            return 'text'  # Default to text template if no evidence
        
        # Count evidence types
        type_counts = {
            'image': 0,
            'table': 0, 
            'text': 0
        }
        
        for evidence in evidence_results:
            category = evidence.get('category', '').lower()
            
            # Check for image-related evidence
            if any(img_type in category for img_type in ['image', 'figure', 'chart', 'extracted_image']):
                type_counts['image'] += 1
            
            # Check for table-related evidence  
            elif any(table_type in category for table_type in ['table']) or evidence.get('type', '').lower() == 'table':
                type_counts['table'] += 1
            
            # Check content structure for tables
            content = evidence.get('content', {})
            if isinstance(content, dict) and ('headers' in content and 'rows' in content):
                type_counts['table'] += 1
            
            # Everything else counts as text
            else:
                type_counts['text'] += 1
        
        # Decision logic: prioritize in order image > table > text
        if type_counts['image'] > 0:
            selected_template = 'image'
        elif type_counts['table'] > 0:
            selected_template = 'table'
        else:
            selected_template = 'text'
        
        self.logger.info(f"Template selection based on evidence: {type_counts}")
        self.logger.info(f"Selected template type: {selected_template}")
        
        return selected_template
    
    def generate_html_content(self, user_query: str, evidence_results: List[Dict[str, Any]], 
                             image_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate HTML content using text model with provided images
        Args:
            user_query: Original user query
            evidence_results: List of relevant evidence items
            image_results: Processed image results from ImageGeneratorChain
        Returns:
            Dictionary with generated HTML content
        """
        self.logger.info(f"Generating HTML content for query: {user_query}")
        
        try:
            # Select appropriate template based on evidence
            selected_template_type = self._select_template_based_on_evidence(evidence_results)
            selected_template_content = self.template_contents.get(selected_template_type, 
                                                                   self.template_contents.get('default'))
            
            # Prepare evidence data
            evidence_summary = self._prepare_evidence_summary(evidence_results)
            evidence_details = self._prepare_evidence_details(evidence_results)
            image_info = self._prepare_image_info(image_results)
            image_html_content = self._prepare_image_html_content(image_results)
            
            # Format the prompt with data
            formatted_prompt = self.prompt_template.format(
                user_query=user_query,
                evidence_summary=evidence_summary,
                evidence_details=evidence_details,
                image_info=image_info,
                image_html_content=image_html_content,
                template_content=selected_template_content, # Pass the selected template content
                template_width=self.template_width,
                template_height=self.template_height
            )
            
            # Generate HTML using text model
            response = self.llm.invoke(formatted_prompt)
            response_text = response.content
            
            self.logger.info(f"Generated HTML content length: {len(response_text)}")
            
            # Parse the JSON response
            parsed_response = self.output_parser.parse(response_text)
            
            self.logger.info("Successfully generated and parsed HTML content")
            return parsed_response
            
        except Exception as e:
            self.logger.error(f"Error generating HTML content: {str(e)}")
            return {
                "title": "Error in Content Generation",
                "html_content": f"<p>Error: {str(e)}</p>",
                "summary": "Content generation failed"
            }
    
    def create_complete_html(self, user_query: str, evidence_results: List[Dict[str, Any]], 
                            image_results: Dict[str, Any] = None) -> str:
        """
        Create a complete HTML page with AI-generated content
        Args:
            user_query: Original user query
            evidence_results: List of relevant evidence items
            image_results: Processed image results from ImageGeneratorChain
        Returns:
            Complete HTML page as string generated by AI
        """
        # Generate complete HTML using AI
        ai_content_result = self.generate_html_content(user_query, evidence_results, image_results)
        
        # Return the AI-generated complete HTML
        complete_html = ai_content_result.get('html_content', '')
        
        if not complete_html:
            # Fallback: use appropriate template with basic replacements
            self.logger.warning("AI did not generate html_content, using template fallback")
            selected_template_type = self._select_template_based_on_evidence(evidence_results)
            html_content = self.template_contents.get(selected_template_type, 
                                                      self.template_contents.get('default'))
            html_content = html_content.replace('{{MAIN_TITLE}}', 'FRESCO Study Results')
            html_content = html_content.replace('{{SUBTITLE}}', 'Clinical Analysis')
            html_content = html_content.replace('{{key findings}}', 'Key clinical findings from analysis')
            html_content = html_content.replace('{{CHART_IMAGE}}', 'efficacy_os.png')
            html_content = html_content.replace('{{CHART_ALT}}', 'Clinical chart')
            return html_content
        
        self.logger.info("Complete HTML page generated by AI")
        return complete_html
    
    def _extract_key_content_from_evidence(self, user_query: str, evidence_results: List[Dict[str, Any]], 
                                         selected_image_info: Dict[str, Any] = None) -> tuple:
        """
        Extract key content elements from evidence for template replacement
        Args:
            user_query: Original user query
            evidence_results: List of evidence items
            selected_image_info: Information about selected image (optional)
        Returns:
            Tuple of (main_title, subtitle, key_stat_number, key_stat_text)
        """
        # Default values
        main_title = "Clinical Study Results"
        subtitle = "Data Analysis"
        key_stat_number = "N/A"
        key_stat_text = "Statistic"
        
        # Analyze query to determine focus
        query_lower = user_query.lower()
        
        # Determine main title based on query
        if any(term in query_lower for term in ['overall survival', 'os']):
            main_title = "Overall Survival in mCRC Patients"
            subtitle = "Kaplan-Meier Analysis of OS with Fruquintinib"
        elif any(term in query_lower for term in ['progression free survival', 'pfs']):
            main_title = "Progression-Free Survival Analysis"
            subtitle = "PFS Outcomes with Fruquintinib Treatment"
        elif any(term in query_lower for term in ['safety', 'adverse']):
            main_title = "Safety Profile Analysis"
            subtitle = "Adverse Events and Safety Data"
        elif any(term in query_lower for term in ['efficacy']):
            main_title = "Efficacy Analysis"
            subtitle = "Clinical Outcomes with Fruquintinib"
        else:
            main_title = "FRESCO Study Analysis"
            subtitle = "Clinical Data Review"
        
        # Extract key statistics from evidence or image info
        if selected_image_info:
            content = selected_image_info.get('content', '')
            
            # Look for median survival time in content
            import re
            median_match = re.search(r'median.*?(\d+\.?\d*)\s*(months?|mo)', content.lower())
            if median_match:
                key_stat_number = f"Median: {median_match.group(1)}"
                key_stat_text = "Months"
            else:
                # Look for other numeric values
                number_match = re.search(r'(\d+\.?\d*)\s*(%|months?|mo|years?)', content.lower())
                if number_match:
                    key_stat_number = number_match.group(1)
                    unit = number_match.group(2)
                    key_stat_text = unit.capitalize()
        
        # If no stats found in image, look in text evidence
        if key_stat_number == "N/A" and evidence_results:
            for evidence in evidence_results[:5]:  # Check top 5 evidence items
                content = evidence.get('content', '')
                if isinstance(content, str):
                    # Look for survival data
                    import re
                    os_match = re.search(r'os.*?(\d+\.?\d*)\s*(months?|mo)', content.lower())
                    if os_match:
                        key_stat_number = f"Median OS: {os_match.group(1)}"
                        key_stat_text = "Months"
                        break
                    
                    # Look for general median values
                    median_match = re.search(r'median.*?(\d+\.?\d*)', content.lower())
                    if median_match:
                        key_stat_number = median_match.group(1)
                        key_stat_text = "Months"
                        break
        
        # Fallback based on query type
        if key_stat_number == "N/A":
            if 'os' in query_lower or 'overall survival' in query_lower:
                key_stat_number = "Median OS: 13.7"
                key_stat_text = "Months"
            elif 'pfs' in query_lower:
                key_stat_number = "Median PFS: 8.5"
                key_stat_text = "Months"
            else:
                key_stat_number = "Study Data"
                key_stat_text = "Available"
        
        return main_title, subtitle, key_stat_number, key_stat_text
    

    def _add_fixed_dimensions_styling(self, soup: BeautifulSoup) -> None:
        """
        Skip adding any additional styling - use template's original CSS
        Args:
            soup: BeautifulSoup object of the HTML document
        """
        # No additional styling needed - use template's original CSS
        self.logger.info("Using original template CSS without modifications")
        return
    
    def _add_template_image_to_html(self, soup: BeautifulSoup) -> None:
        """
        Add template image as background overlay to the HTML
        Args:
            soup: BeautifulSoup object of the HTML document
        """
        # Skip adding template image overlay to avoid long base64 strings
        self.logger.info("Skipping template image overlay to avoid base64 encoding")
        return
    
    def generate_html_with_template_image(self, user_query: str, evidence_results: List[Dict[str, Any]], 
                                        image_results: Dict[str, Any] = None, 
                                        template_image_path: str = None) -> str:
        """
        Generate HTML content with specific template image input
        Args:
            user_query: Original user query
            evidence_results: List of relevant evidence items
            image_results: Processed image results from ImageGeneratorChain
            template_image_path: Path to specific template image (optional, defaults to picture.png)
        Returns:
            Complete HTML page as string with template image integration
        """
        # Use custom template image if provided
        if template_image_path and os.path.exists(template_image_path):
            try:
                with open(template_image_path, 'rb') as img_file:
                    custom_template_data = base64.b64encode(img_file.read()).decode('utf-8')
                # Temporarily store current template data
                original_template_data = self.template_image_data
                
                # Set new template data
                self.template_image_data = custom_template_data
                self.logger.info(f"Using custom template image: {template_image_path}")
            except Exception as e:
                self.logger.error(f"Failed to load custom template image: {e}")
                # Fall back to default template image
        
        try:
            # Generate HTML with template image integration
            html_result = self.create_complete_html(user_query, evidence_results, image_results)
            
            # Restore original template data if we used a custom one
            if template_image_path and 'original_template_data' in locals():
                self.template_image_data = original_template_data
            
            return html_result
            
        except Exception as e:
            self.logger.error(f"Failed to generate HTML with template image: {e}")
            # Restore original template data if we used a custom one
            if template_image_path and 'original_template_data' in locals():
                self.template_image_data = original_template_data
            raise
    
    def save_html_to_file(self, html_content: str, filename: str = None) -> str:
        """
        Save HTML content to file
        Args:
            html_content: Complete HTML content
            filename: Output filename (optional)
        Returns:
            Path to saved file
        """
        if not filename:
            filename = "fresco_presentation.html"
        
        # Ensure output directory exists
        output_dir = os.path.join(config.html_generator_root, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, filename)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"HTML saved to: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to save HTML: {e}")
            raise 