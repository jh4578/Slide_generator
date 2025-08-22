"""
PDF Processing Module using Docling
Extracts text paragraphs, images, and tables from PDF documents
All evidence is stored in a unified JSON format with intelligent labeling
"""

import os
import json
import re
import ssl
import urllib.request
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

# Fix SSL certificate verification issue
ssl._create_default_https_context = ssl._create_unverified_context

try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    DOCLING_AVAILABLE = True
except ImportError:
    print("Warning: Docling not installed. Run: pip install docling docling-core")
    DOCLING_AVAILABLE = False

from PIL import Image
import base64
from io import BytesIO


class PDFProcessor:
    """Main class for processing PDF documents using docling"""
    
    def __init__(self, input_dir: str = "context", 
                 output_dir: str = ".", 
                 images_dir: str = "images",
                 min_image_width: int = 100,
                 min_image_height: int = 100):
        """
        Initialize PDF processor with docling configuration
        
        Args:
            input_dir: Directory containing PDF files
            output_dir: Directory for output JSON
            images_dir: Directory for extracted images
            min_image_width: Minimum width for image extraction (default: 100px)
            min_image_height: Minimum height for image extraction (default: 100px)
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.images_dir = Path(images_dir)
        
        # Image size filtering settings
        self.min_image_width = min_image_width
        self.min_image_height = min_image_height
        
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        if not DOCLING_AVAILABLE:
            raise ImportError("Docling is required but not installed")
        
        # Initialize document converter with default settings
        self.converter = DocumentConverter()
        
        # Evidence counter for unique IDs
        self.evidence_counter = 1
        
        # Content classification keywords
        self.classification_keywords = {
            "indication": ["indication", "indicated", "treatment", "therapy", "disease"],
            "dosage": ["dosage", "dose", "administration", "mg", "taken", "daily"],
            "efficacy_data": ["efficacy", "response", "survival", "progression", "outcome"],
            "safety_data": ["safety", "adverse", "side effect", "toxicity", "tolerance"],
            "patient_demographics": ["patient", "demographic", "baseline", "characteristic"],
            "clinical_trial": ["trial", "study", "phase", "clinical", "randomized"],
            "mechanism": ["mechanism", "action", "target", "pathway", "inhibit"],
            "pharmacokinetics": ["pharmacokinetic", "absorption", "metabolism", "clearance"],
            "adverse_events": ["adverse event", "AE", "serious adverse", "grade"],
            "contraindications": ["contraindication", "contraindicated", "should not"]
        }
    
    def process_all_pdfs(self) -> Dict[str, Any]:
        """
        Process all PDF files in the input directory
        
        Returns:
            Dictionary containing all extracted evidence
        """
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {self.input_dir}")
        
        pdf_files = list(self.input_dir.glob("*.pdf"))
        if not pdf_files:
            raise FileNotFoundError(f"No PDF files found in {self.input_dir}")
        
        print(f"Found {len(pdf_files)} PDF files to process")
        
        all_evidence = []
        
        for pdf_file in pdf_files:
            print(f"Processing: {pdf_file.name}")
            try:
                evidence_list = self._process_single_pdf(pdf_file)
                all_evidence.extend(evidence_list)
                print(f"Extracted {len(evidence_list)} evidence items from {pdf_file.name}")
            except Exception as e:
                print(f"Error processing {pdf_file.name}: {str(e)}")
                continue
        
        # Create final output structure
        output_data = {
            "extraction_info": {
                "timestamp": datetime.now().isoformat(),
                "docling_version": "2.0.0",
                "total_documents": len(pdf_files),
                "total_evidence": len(all_evidence),
                "processing_status": "completed"
            },
            "evidence": all_evidence
        }
        
        # Save to JSON file
        output_file = self.output_dir / "extracted_content.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"Processing complete. Results saved to: {output_file}")
        print(f"Total evidence extracted: {len(all_evidence)}")
        
        return output_data
    
    def _process_single_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """
        Process a single PDF file using docling
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of evidence dictionaries
        """
        evidence_list = []
        
        # Convert PDF using docling
        result = self.converter.convert(pdf_path)
        doc = result.document
        
        # Extract text paragraphs
        evidence_list.extend(self._extract_text_evidence(doc, pdf_path.name))
        
        # Extract real images using PyMuPDF (ignore docling's false detections)
        evidence_list.extend(self._extract_real_images_pymupdf(pdf_path))
        
        # Extract tables (pass doc for context)
        evidence_list.extend(self._extract_table_evidence(doc, pdf_path.name, doc))
        
        return evidence_list
    
    def _extract_text_evidence(self, doc, source_file: str) -> List[Dict[str, Any]]:
        """Extract text paragraphs from docling document"""
        evidence_list = []
        
        # Extract text content from document
        
        # Try different ways to access text content
        text_elements = []
        
        # Access text elements from docling document
        if hasattr(doc, 'texts') and doc.texts:
            text_elements = doc.texts
        elif hasattr(doc, 'main_text') and doc.main_text:
            text_elements = doc.main_text
        elif hasattr(doc, 'body') and doc.body:
            text_elements = doc.body
        elif hasattr(doc, 'export_to_markdown'):
            # Fallback: export to markdown and parse
            markdown_content = doc.export_to_markdown()
            if markdown_content:
                # Split markdown into paragraphs
                paragraphs = [p.strip() for p in markdown_content.split('\n\n') if p.strip()]
                for i, paragraph in enumerate(paragraphs):
                    if len(paragraph) >= 50:  # Filter short paragraphs
                        evidence = {
                            "id": f"evidence_{self.evidence_counter:03d}",
                            "type": "text",
                            "source_document": source_file,
                            "page_number": 1,  # Default page
                            "content": paragraph,
                            "label": self._generate_text_label(paragraph),
                            "category": self._classify_content(paragraph)
                        }
                        evidence_list.append(evidence)
                        self.evidence_counter += 1
                return evidence_list
        
        # Process text elements if found
        for text_element in text_elements:
                text_content = text_element.text.strip()
                
                # Filter out very short texts
                if len(text_content) < 50:
                    continue
                
                # Get page number from provenance
                page_number = 1  # Default
                if hasattr(text_element, 'prov') and text_element.prov:
                    page_number = text_element.prov[0].page_no + 1
                
                evidence = {
                    "id": f"evidence_{self.evidence_counter:03d}",
                    "type": "text",
                    "source_document": source_file,
                    "page_number": page_number,
                    "content": text_content,
                    "label": self._generate_text_label(text_content),
                    "category": self._classify_content(text_content)
                }
                
                evidence_list.append(evidence)
                self.evidence_counter += 1
        
        return evidence_list
    
    def _extract_image_evidence(self, doc, source_file: str, parent_doc) -> List[Dict[str, Any]]:
        """Extract images from docling document"""
        evidence_list = []
        
        # Get all picture elements from docling
        if hasattr(doc, 'pictures'):
            for picture_element in doc.pictures:
                # Get page number from provenance
                page_number = 1  # Default
                if hasattr(picture_element, 'prov') and picture_element.prov:
                    page_number = picture_element.prov[0].page_no + 1
                
                # Save image file
                image_filename = f"img_{self.evidence_counter:03d}.png"
                image_path = self._save_image(picture_element, image_filename, parent_doc)
                
                # Create evidence regardless of whether image was saved
                evidence = {
                    "id": f"evidence_{self.evidence_counter:03d}",
                    "type": "image",
                    "source_document": source_file,
                    "page_number": page_number,
                    "original_content": image_path if image_path else f"Image extraction failed: {image_filename}",
                    "content": "",
                    "label": self._generate_image_label(picture_element),
                    "category": self._classify_image_content(picture_element)
                }
                
                # Add metadata if available  
                try:
                    if hasattr(picture_element, 'caption_text'):
                        caption_func = getattr(picture_element, 'caption_text')
                        if callable(caption_func):
                            caption = caption_func()
                            if caption:
                                evidence["caption"] = str(caption)
                        elif caption_func:
                            evidence["caption"] = str(caption_func)
                except Exception:
                    pass
                
                evidence_list.append(evidence)
                
                self.evidence_counter += 1
        
        return evidence_list
    
    def _extract_table_evidence(self, doc, source_file: str, parent_doc) -> List[Dict[str, Any]]:
        """Extract tables from docling document"""
        evidence_list = []
        
        # Get all table elements from docling
        if hasattr(doc, 'tables'):
            for table_element in doc.tables:
                # Get page number from provenance
                page_number = 1  # Default
                if hasattr(table_element, 'prov') and table_element.prov:
                    page_number = table_element.prov[0].page_no + 1
                
                # Format table data
                table_data = self._format_docling_table(table_element, parent_doc)
                
                evidence = {
                    "id": f"evidence_{self.evidence_counter:03d}",
                    "type": "table",
                    "source_document": source_file,
                    "page_number": page_number,
                    "original_content": table_data,
                    "content": "",
                    "label": self._generate_table_label(table_element),
                    "category": self._classify_table_content(table_element)
                }
                
                evidence_list.append(evidence)
                self.evidence_counter += 1
        
        return evidence_list
    
    def _extract_real_images_pymupdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract real bitmap images using PyMuPDF, ignoring docling's false detections"""
        evidence_list = []
        
        try:
            import fitz
            pdf_doc = fitz.open(str(pdf_path))
            
            for page_no in range(len(pdf_doc)):
                page = pdf_doc[page_no]
                images = page.get_images()
                
                for img_index, img in enumerate(images):
                    try:
                        xref = img[0]
                        pix = fitz.Pixmap(pdf_doc, xref)
                        
                        # Check image dimensions - skip if too small (likely symbols/icons)
                        if pix.width < self.min_image_width or pix.height < self.min_image_height:
                            print(f"⏭️ Skipping small image: {pix.width}x{pix.height} (below {self.min_image_width}x{self.min_image_height} threshold)")
                            pix = None
                            continue
                        
                        # Create filename using evidence counter
                        filename = f"img_{self.evidence_counter:03d}.png"
                        image_path = self.images_dir / filename
                        
                        # Save the image
                        if pix.n - pix.alpha < 4:  # RGB or GRAY
                            pix.save(str(image_path))
                            size_kb = image_path.stat().st_size // 1024
                            print(f"✅ Image extracted: {filename} ({pix.width}x{pix.height}, {size_kb}KB)")
                        else:  # CMYK
                            pix1 = fitz.Pixmap(fitz.csRGB, pix)
                            pix1.save(str(image_path))
                            size_kb = image_path.stat().st_size // 1024
                            print(f"✅ Image extracted (CMYK): {filename} ({pix1.width}x{pix1.height}, {size_kb}KB)")
                            pix1 = None
                        
                        # Create evidence entry
                        evidence = {
                            "id": f"evidence_{self.evidence_counter:03d}",
                            "type": "image",
                            "source_document": pdf_path.name,
                            "page_number": page_no + 1,
                            "content": f"images/{filename}",
                            "label": f"Figure: Image from Page {page_no + 1}",
                            "category": "extracted_image"
                        }
                        
                        evidence_list.append(evidence)
                        self.evidence_counter += 1
                        pix = None
                        
                    except Exception as e:
                        print(f"Failed to extract image from page {page_no+1}: {e}")
            
            pdf_doc.close()
            
        except Exception as e:
            print(f"Error in PyMuPDF image extraction: {e}")
        
        return evidence_list
    
    def _save_image(self, picture_element, filename: str, doc) -> Optional[str]:
        """Extract real bitmap images from PDF, ignore docling's fake detections"""
        try:
            image_path = self.images_dir / filename
            
            # Get page number from docling detection
            page_no = 0
            if hasattr(picture_element, 'prov') and picture_element.prov:
                page_no = picture_element.prov[0].page_no
            
            # Find the source PDF file
            pdf_files = list(self.input_dir.glob('*.pdf'))
            if not pdf_files:
                pdf_files = list(self.input_dir.parent.glob('*.pdf'))
            
            if pdf_files:
                import fitz
                source_pdf = str(pdf_files[0])
                pdf_doc = fitz.open(source_pdf)
                
                # Check ALL pages for real bitmap images, not just the docling detected page
                real_images_found = []
                for check_page_no in range(len(pdf_doc)):
                    page = pdf_doc[check_page_no]
                    images = page.get_images()
                    
                    for img_index, img in enumerate(images):
                        try:
                            xref = img[0]
                            pix = fitz.Pixmap(pdf_doc, xref)
                            
                            # Check image dimensions - skip if too small (likely symbols/icons)
                            if pix.width < self.min_image_width or pix.height < self.min_image_height:
                                print(f"⏭️ Skipping small image in _save_image: {pix.width}x{pix.height} (below {self.min_image_width}x{self.min_image_height} threshold)")
                                pix = None
                                continue
                            
                            # This is a real image, save it
                            real_filename = f"real_image_page{check_page_no+1}_{img_index+1}.png"
                            real_path = self.images_dir / real_filename
                            
                            if pix.n - pix.alpha < 4:  # RGB or GRAY
                                pix.save(str(real_path))
                                print(f"✅ Found real image: {real_filename} ({pix.width}x{pix.height})")
                                real_images_found.append(real_filename)
                            else:  # CMYK
                                pix1 = fitz.Pixmap(fitz.csRGB, pix)
                                pix1.save(str(real_path))
                                print(f"✅ Found real image (CMYK): {real_filename} ({pix1.width}x{pix1.height})")
                                real_images_found.append(real_filename)
                                pix1 = None
                            pix = None
                        except Exception as e:
                            print(f"Failed to extract image from page {check_page_no+1}: {e}")
                
                pdf_doc.close()
                
                # If we found real images, use the first one for this docling detection
                if real_images_found:
                    # Copy the first real image to the requested filename
                    import shutil
                    real_image_path = self.images_dir / real_images_found[0]
                    shutil.copy2(real_image_path, image_path)
                    print(f"✅ Using real image for {filename}")
                    return f"images/{filename}"
            
            # If no real images found, create a placeholder
            print(f"⚠️ No real images in PDF, creating placeholder for {filename}")
            from PIL import Image, ImageDraw, ImageFont
            
            placeholder_image = Image.new('RGB', (400, 200), color='white')
            draw = ImageDraw.Draw(placeholder_image)
            draw.rectangle([0, 0, 399, 199], outline='gray', width=2)
            
            try:
                font = ImageFont.load_default()
                draw.text((20, 30), "📊 Docling误检测", fill='black', font=font)
                draw.text((20, 60), f"第 {page_no + 1} 页", fill='gray', font=font)
                draw.text((20, 90), "实际是表格/文本", fill='blue', font=font)
                draw.text((20, 120), "无真实图片", fill='red', font=font)
            except:
                draw.text((20, 30), "Docling false detection", fill='black')
            
            placeholder_image.save(image_path, format="PNG")
            return f"images/{filename}"
            
        except Exception as e:
            print(f"Error in _save_image for {filename}: {str(e)}")
            return None
    
    def _format_docling_table(self, table_element, parent_doc) -> Dict[str, Any]:
        """Format table data from docling table element"""
        try:
            headers = []
            rows = []
            
            # Method 1: Try accessing table data through TableData structure
            if hasattr(table_element, 'data') and table_element.data:
                try:
                    data = table_element.data
                    # Handle TableData object - extract cell texts
                    if hasattr(data, 'table_cells'):
                        table_cells = data.table_cells
                        if table_cells:
                            # Organize cells by row and column
                            cells_by_row = {}
                            max_row = 0
                            max_col = 0
                            
                            for cell in table_cells:
                                if hasattr(cell, 'start_row_offset_idx') and hasattr(cell, 'start_col_offset_idx'):
                                    row_idx = cell.start_row_offset_idx
                                    col_idx = cell.start_col_offset_idx
                                    text = getattr(cell, 'text', '')
                                    
                                    if row_idx not in cells_by_row:
                                        cells_by_row[row_idx] = {}
                                    cells_by_row[row_idx][col_idx] = text
                                    
                                    max_row = max(max_row, row_idx)
                                    max_col = max(max_col, col_idx)
                            
                            # Convert to headers and rows
                            if cells_by_row:
                                # First row as headers
                                if 0 in cells_by_row:
                                    headers = []
                                    for col in range(max_col + 1):
                                        headers.append(cells_by_row[0].get(col, ''))
                                
                                # Remaining rows as data
                                for row_idx in range(1, max_row + 1):
                                    if row_idx in cells_by_row:
                                        row_data = []
                                        for col in range(max_col + 1):
                                            row_data.append(cells_by_row[row_idx].get(col, ''))
                                        if any(cell.strip() for cell in row_data):  # Only add non-empty rows
                                            rows.append(row_data)
                except Exception as e:
                    print(f"TableData extraction failed: {e}")
            
            # Method 2: Try export_to_dataframe and convert
            if not headers and hasattr(table_element, 'export_to_dataframe'):
                try:
                    df = table_element.export_to_dataframe()
                    if df is not None and not df.empty:
                        headers = [str(col) for col in df.columns.tolist()]
                        rows = df.values.tolist()
                        # Convert all values to strings
                        rows = [[str(cell) for cell in row] for row in rows]
                except Exception as e:
                    print(f"DataFrame export failed: {e}")
            
            # Method 3: Try to use export_to_markdown and parse
            if not headers and hasattr(table_element, 'export_to_markdown'):
                try:
                    # Pass the parent document to avoid deprecation warning
                    if parent_doc:
                        markdown_content = table_element.export_to_markdown(parent_doc)
                    elif hasattr(table_element, 'parent') and table_element.parent:
                        markdown_content = table_element.export_to_markdown(table_element.parent)
                    else:
                        markdown_content = table_element.export_to_markdown()
                    
                    if markdown_content and '|' in markdown_content:
                        lines = markdown_content.strip().split('\n')
                        for i, line in enumerate(lines):
                            if '|' in line and not line.strip().startswith('|---'):
                                cells = [cell.strip() for cell in line.split('|')[1:-1]]  # Remove empty first/last
                                if cells and not all('---' in cell or ':-' in cell for cell in cells):
                                    if not headers:
                                        headers = cells
                                    else:
                                        if len(cells) == len(headers):
                                            rows.append(cells)
                except Exception as e:
                    print(f"Markdown export failed: {e}")
            
            # Method 4: Try text-based extraction
            if not headers and hasattr(table_element, 'text') and table_element.text:
                try:
                    text_content = table_element.text.strip()
                    # Try different separators
                    for separator in ['\t', '  ', ' | ']:
                        lines = text_content.split('\n')
                        if len(lines) > 1:
                            potential_headers = [cell.strip() for cell in lines[0].split(separator) if cell.strip()]
                            if len(potential_headers) > 1:
                                headers = potential_headers
                                for line in lines[1:]:
                                    row_data = [cell.strip() for cell in line.split(separator) if cell.strip()]
                                    if len(row_data) == len(headers):
                                        rows.append(row_data)
                                break
                except:
                    pass
            
            # If still no data, try to extract meaningful content from text
            if not headers and hasattr(table_element, 'text') and table_element.text:
                text_content = table_element.text.strip()
                if text_content:
                    # Create a single-column table with the text content
                    headers = ["Content"]
                    # Split long text into meaningful chunks
                    chunks = text_content.split('\n')
                    rows = [[chunk.strip()] for chunk in chunks if chunk.strip()]
            
            # Final fallback
            if not headers:
                headers = ["Content"]
                rows = [["Table structure could not be parsed"]]
            
            # Generate markdown representation
            markdown = self._table_to_markdown(headers, rows)
            
            return {
                "headers": headers,
                "rows": rows,
                "markdown": markdown
            }
            
        except Exception as e:
            print(f"Error formatting table: {str(e)}")
            # Return the error but with any available text content
            error_content = "Table extraction failed"
            if hasattr(table_element, 'text') and table_element.text:
                error_content = table_element.text[:200] + "..." if len(table_element.text) > 200 else table_element.text
            
            return {
                "headers": ["Content"],
                "rows": [[error_content]],
                "markdown": f"| Content |\n|---|\n| {error_content} |"
            }
    
    def _table_to_markdown(self, headers: List[str], rows: List[List[str]]) -> str:
        """Convert table data to markdown format"""
        if not headers:
            return "Empty table"
        
        markdown = "| " + " | ".join(headers) + " |\n"
        markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        
        for row in rows:
            # Pad row to match header length
            padded_row = row + [""] * (len(headers) - len(row))
            markdown += "| " + " | ".join(padded_row[:len(headers)]) + " |\n"
        
        return markdown
    
    def _generate_text_label(self, text_content: str) -> str:
        """Generate intelligent label for text content"""
        text_lower = text_content.lower()
        
        # Check for specific content types
        if any(keyword in text_lower for keyword in ["indication", "indicated"]):
            return "Drug Indication Information"
        elif any(keyword in text_lower for keyword in ["dosage", "dose", "administration"]):
            return "Dosage and Administration"
        elif any(keyword in text_lower for keyword in ["adverse", "side effect"]):
            return "Adverse Events Information"
        elif any(keyword in text_lower for keyword in ["efficacy", "survival", "response"]):
            return "Efficacy Data"
        elif any(keyword in text_lower for keyword in ["safety", "tolerability"]):
            return "Safety Information"
        else:
            # Generate label based on first sentence
            first_sentence = text_content.split('.')[0][:100]
            return f"Clinical Information: {first_sentence}..."
    
    def _generate_image_label(self, picture_element) -> str:
        """Generate intelligent label for image content"""
        # Try to extract caption from docling metadata
        if hasattr(picture_element, 'caption') and picture_element.caption:
            return picture_element.caption
        
        # Default image label
        return "Figure: Clinical Data Visualization"
    
    def _generate_table_label(self, table_element) -> str:
        """Generate intelligent label for table content"""
        # Try to extract table title from docling structure
        if hasattr(table_element, 'caption') and table_element.caption:
            return table_element.caption
        
        # Default table label
        return "Clinical Data Table"
    
    def _classify_content(self, content: str) -> str:
        """Classify content into predefined categories"""
        content_lower = content.lower()
        
        # Count keyword matches for each category
        category_scores = {}
        for category, keywords in self.classification_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                category_scores[category] = score
        
        # Return category with highest score, or 'general' if no matches
        if category_scores:
            return max(category_scores, key=category_scores.get)
        else:
            return "general"
    
    def _classify_image_content(self, picture_element) -> str:
        """Classify image content based on context"""
        # For now, return general classification
        # Could be enhanced with image analysis
        return "clinical_visualization"
    
    def _classify_table_content(self, table_element) -> str:
        """Classify table content based on structure and content"""
        # For now, return general classification
        # Could be enhanced by analyzing table headers/content
        return "clinical_data"


def main():
    """Main function to run PDF processing"""
    # 可以在这里调整图片尺寸阈值，过滤掉小图标和符号
    # 默认: 100x100 像素，可以根据需要调整
    processor = PDFProcessor(
        min_image_width=100,   # 最小宽度 (像素)
        min_image_height=100   # 最小高度 (像素)
    )
    try:
        result = processor.process_all_pdfs()
        print(f"Successfully processed {result['extraction_info']['total_documents']} documents")
        print(f"Total evidence items: {result['extraction_info']['total_evidence']}")
    except Exception as e:
        print(f"Error during processing: {str(e)}")


if __name__ == "__main__":
    main() 