"""
MultiPageOrchestrator for coordinating parallel multi-page HTML generation
Manages the complete workflow from page planning to final HTML page combination
"""

import logging
import time
import json
import os
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from chains.page_planner import PagePlannerAgent, PagePlan, PageInfo
from orchestrator import FrescoHTMLOrchestrator
from html_merger import HTMLMerger
from config import config

logger = logging.getLogger(__name__)

class PageResult:
    """Result container for individual page processing"""
    
    def __init__(self, page_info: PageInfo):
        self.page_info = page_info
        self.success = False
        self.html_content = ""
        self.evidence_count = 0
        self.processing_time = 0.0
        self.error = None
        self.image_results = None
        self.evidence_results = []

class MultiPageOrchestrator:
    """
    Orchestrator for managing multi-page HTML generation
    Coordinates page planning, parallel processing, and final HTML combination
    """
    
    def __init__(self):
        """Initialize the multi-page orchestrator"""
        self.logger = logging.getLogger(__name__)
        self.page_planner = PagePlannerAgent()
        self.html_merger = HTMLMerger()
        
        # We'll create single-page orchestrators as needed to avoid resource conflicts
        self.max_concurrent_pages = config.get('max_concurrent_pages', 3)
        
        self.logger.info("MultiPageOrchestrator initialized")
    
    def process_query(self, user_query: str, save_html: bool = True, 
                     filename: str = None) -> Dict[str, Any]:
        """
        Process user query with automatic page planning and parallel execution
        
        Args:
            user_query: User's original query
            save_html: Whether to save final output to file
            filename: Optional filename for output
            
        Returns:
            Complete processing results with all pages
        """
        start_time = time.time()
        self.logger.info(f"Processing multi-page query: {user_query}")
        
        try:
            # Step 1: Analyze query and plan pages
            self.logger.info("Step 1: Planning pages...")
            page_plan = self.page_planner.analyze_query(user_query)
            
            if not self.page_planner.validate_page_plan(page_plan):
                self.logger.warning("Invalid page plan, falling back to single page")
                page_plan = self.page_planner.get_single_page_plan(user_query)
            
            self.logger.info(f"Page planning complete: {page_plan.total_pages} pages")
            self.logger.info(f"Plan reasoning: {page_plan.reasoning}")
            
            # Step 2: Process pages (single or multi-page)
            if page_plan.is_multi_page and page_plan.total_pages > 1:
                self.logger.info("Step 2: Processing multiple pages in parallel...")
                page_results = self._process_pages_parallel(page_plan.pages)
            else:
                self.logger.info("Step 2: Processing single page...")
                page_results = self._process_single_page(page_plan.pages[0])
            
            # Step 3: Combine HTML results
            self.logger.info("Step 3: Combining page results...")
            if page_plan.is_multi_page and len(page_results) > 1:
                final_html = self._combine_multiple_pages_html(page_results, page_plan)
            else:
                final_html = page_results[0].html_content if page_results else ""
            
            # Save HTML if requested
            output_path = None
            if save_html and final_html:
                output_path = self._save_html_to_file(final_html, filename, page_plan)
            
            # Prepare complete result
            total_time = time.time() - start_time
            result = self._build_result_summary(
                user_query, page_plan, page_results, final_html,
                output_path, total_time
            )
            
            self.logger.info(f"Multi-page processing completed in {total_time:.2f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"Multi-page processing failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'user_query': user_query,
                'error': str(e),
                'processing_time': {'total': time.time() - start_time},
                'is_multi_page': False
            }
    
    def _process_pages_parallel(self, pages: List[PageInfo]) -> List[PageResult]:
        """
        Process multiple pages in parallel using ThreadPoolExecutor
        
        Args:
            pages: List of PageInfo objects to process
            
        Returns:
            List of PageResult objects
        """
        self.logger.info(f"Starting parallel processing of {len(pages)} pages")
        
        page_results = []
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=min(self.max_concurrent_pages, len(pages))) as executor:
            # Submit all page processing tasks
            future_to_page = {
                executor.submit(self._process_single_page_sync, page): page 
                for page in pages
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    result = future.result()
                    page_results.append(result)
                    self.logger.info(f"Page {page.page_number} completed: {result.success}")
                except Exception as e:
                    self.logger.error(f"Page {page.page_number} failed: {str(e)}")
                    # Create failed result
                    failed_result = PageResult(page)
                    failed_result.error = str(e)
                    page_results.append(failed_result)
        
        # Sort results by page number
        page_results.sort(key=lambda r: r.page_info.page_number)
        
        success_count = sum(1 for r in page_results if r.success)
        self.logger.info(f"Parallel processing complete: {success_count}/{len(pages)} pages successful")
        
        return page_results
    
    def _process_single_page_sync(self, page_info: PageInfo) -> PageResult:
        """
        Process a single page synchronously (for use in thread pool)
        
        Args:
            page_info: PageInfo object to process
            
        Returns:
            PageResult object
        """
        result = PageResult(page_info)
        start_time = time.time()
        
        try:
            self.logger.info(f"Processing page {page_info.page_number}: {page_info.title}")
            
            # Create a fresh orchestrator instance for this page
            orchestrator = FrescoHTMLOrchestrator()
            
            # Process the page query
            page_result = orchestrator.process_query(
                page_info.specific_query,
                save_html=False  # We'll handle saving at the multi-page level
            )
            
            if page_result.get('success'):
                result.success = True
                result.html_content = page_result.get('html_content', '')
                result.evidence_count = page_result.get('evidence_count', 0)
                result.evidence_results = page_result.get('evidence_results', [])
                result.image_results = page_result.get('image_results', {})
            else:
                result.error = page_result.get('error', 'Unknown error')
            
            result.processing_time = time.time() - start_time
            
        except Exception as e:
            result.error = str(e)
            result.processing_time = time.time() - start_time
            self.logger.error(f"Error processing page {page_info.page_number}: {str(e)}")
        
        return result
    
    def _process_single_page(self, page_info: PageInfo) -> List[PageResult]:
        """
        Process a single page and return as list for consistency
        
        Args:
            page_info: Single page to process
            
        Returns:
            List with single PageResult
        """
        result = self._process_single_page_sync(page_info)
        return [result]
    
    def _combine_multiple_pages_html(self, page_results: List[PageResult], 
                                   page_plan: PagePlan) -> str:
        """
        Combine multiple page HTML results using HTMLMerger
        
        Args:
            page_results: List of PageResult objects
            page_plan: Original page plan
            
        Returns:
            Combined HTML string
        """
        self.logger.info(f"Combining {len(page_results)} pages using HTMLMerger")
        
        try:
            # Extract HTML content from successful results
            html_contents = []
            for result in page_results:
                if result.success and result.html_content:
                    html_contents.append(result.html_content)
                else:
                    # Create error HTML for failed pages
                    error_html = self._create_error_page_html(result)
                    html_contents.append(error_html)
            
            if not html_contents:
                return self._generate_error_html("No valid page content generated")
            
            # Use HTMLMerger to combine pages
            combined_html = self.html_merger.merge_html_pages(
                html_contents, 
                page_plan.overall_theme
            )
            
            self.logger.info("Successfully combined pages using HTMLMerger")
            return combined_html
            
        except Exception as e:
            self.logger.error(f"Error combining pages with HTMLMerger: {str(e)}")
            return self._generate_error_html(str(e))
    
    def _create_error_page_html(self, result: PageResult) -> str:
        """Create a basic HTML page for errors"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error - {result.page_info.title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                .error {{ color: red; background: #ffe6e6; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="main">
                <h1>Page {result.page_info.page_number}: {result.page_info.title}</h1>
                <div class="error">
                    <h2>Error</h2>
                    <p>{result.error or 'Failed to generate content'}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _combine_multiple_pages(self, page_results: List[PageResult], 
                               page_plan: PagePlan) -> str:
        """
        Combine multiple page HTML results into a single presentation
        
        Args:
            page_results: List of PageResult objects
            page_plan: Original page plan
            
        Returns:
            Combined HTML string
        """
        self.logger.info(f"Combining {len(page_results)} pages into final presentation")
        
        try:
            # Extract individual page content (remove full HTML structure)
            page_contents = []
            for result in page_results:
                if result.success and result.html_content:
                    # Extract main content from HTML (between body tags)
                    content = self._extract_main_content(result.html_content)
                    page_contents.append({
                        'page_number': result.page_info.page_number,
                        'title': result.page_info.title,
                        'content': content,
                        'evidence_count': result.evidence_count
                    })
                else:
                    # Create error page content
                    error_content = f"""
                    <div class="error-page">
                        <h2>Page {result.page_info.page_number}: {result.page_info.title}</h2>
                        <p class="error-message">Error: {result.error or 'Failed to generate content'}</p>
                    </div>
                    """
                    page_contents.append({
                        'page_number': result.page_info.page_number,
                        'title': result.page_info.title,
                        'content': error_content,
                        'evidence_count': 0
                    })
            
            # Generate combined HTML
            combined_html = self._generate_multi_page_html(page_contents, page_plan)
            
            return combined_html
            
        except Exception as e:
            self.logger.error(f"Error combining pages: {str(e)}")
            # Return error HTML
            return self._generate_error_html(str(e))
    
    def _extract_main_content(self, html_content: str) -> str:
        """
        Extract main content from full HTML page
        
        Args:
            html_content: Full HTML string
            
        Returns:
            Main content only
        """
        try:
            # Find content between main tags or body tags
            start_markers = ['<main>', '<div class="container">', '<body>']
            end_markers = ['</main>', '</div>', '</body>']
            
            for start_marker, end_marker in zip(start_markers, end_markers):
                start_idx = html_content.find(start_marker)
                if start_idx != -1:
                    start_idx += len(start_marker)
                    end_idx = html_content.find(end_marker, start_idx)
                    if end_idx != -1:
                        return html_content[start_idx:end_idx].strip()
            
            # Fallback: return content between body tags if found
            start_idx = html_content.find('<body>')
            end_idx = html_content.find('</body>')
            if start_idx != -1 and end_idx != -1:
                start_idx += 6  # len('<body>')
                return html_content[start_idx:end_idx].strip()
            
            # Last resort: return as-is
            return html_content
            
        except Exception as e:
            self.logger.error(f"Error extracting content: {str(e)}")
            return html_content
    
    def _generate_multi_page_html(self, page_contents: List[Dict], 
                                 page_plan: PagePlan) -> str:
        """
        Generate final multi-page HTML with navigation
        
        Args:
            page_contents: List of page content dictionaries
            page_plan: Original page plan
            
        Returns:
            Complete multi-page HTML
        """
        # Build navigation menu
        nav_items = []
        for content in page_contents:
            nav_items.append(f"""
                <li><a href="#page-{content['page_number']}" onclick="showPage({content['page_number']})">
                    {content['title']}
                </a></li>
            """)
        
        navigation = f"""
        <nav class="page-navigation">
            <h3>Presentation Navigation</h3>
            <ul>
                {''.join(nav_items)}
            </ul>
        </nav>
        """
        
        # Build page content sections
        page_sections = []
        for i, content in enumerate(page_contents):
            display_style = "block" if i == 0 else "none"
            page_sections.append(f"""
            <div id="page-{content['page_number']}" class="page-content" style="display: {display_style};">
                <div class="page-header">
                    <h1>{content['title']}</h1>
                    <span class="page-number">Page {content['page_number']} of {len(page_contents)}</span>
                </div>
                {content['content']}
            </div>
            """)
        
        # Build page controls
        page_controls = f"""
        <div class="page-controls">
            <button onclick="previousPage()" id="prev-btn">← Previous</button>
            <span class="page-indicator">
                Page <span id="current-page">1</span> of {len(page_contents)}
            </span>
            <button onclick="nextPage()" id="next-btn">Next →</button>
        </div>
        """
        
        # Complete HTML template
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_plan.overall_theme}</title>
    <style>
        {self._get_multi_page_css()}
    </style>
</head>
<body>
    <div class="presentation-container">
        <header class="presentation-header">
            <h1>{page_plan.overall_theme}</h1>
            <p class="presentation-subtitle">FRESCO Study Analysis - {len(page_contents)} Pages</p>
        </header>
        
        {navigation}
        
        <main class="presentation-main">
            {''.join(page_sections)}
        </main>
        
        {page_controls}
    </div>
    
    <script>
        {self._get_multi_page_javascript(len(page_contents))}
    </script>
</body>
</html>
        """
        
        return html_template
    
    def _get_multi_page_css(self) -> str:
        """Get CSS styles for multi-page presentation"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .presentation-container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        
        .presentation-header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .presentation-header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .presentation-subtitle {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .page-navigation {
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #dee2e6;
        }
        
        .page-navigation h3 {
            margin-bottom: 15px;
            color: #495057;
        }
        
        .page-navigation ul {
            list-style: none;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
        }
        
        .page-navigation a {
            text-decoration: none;
            color: #007bff;
            padding: 8px 16px;
            border: 1px solid #007bff;
            border-radius: 20px;
            transition: all 0.3s;
        }
        
        .page-navigation a:hover {
            background: #007bff;
            color: white;
        }
        
        .presentation-main {
            min-height: 500px;
            padding: 30px;
        }
        
        .page-content {
            animation: fadeIn 0.5s ease-in-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .page-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e9ecef;
        }
        
        .page-header h1 {
            color: #495057;
            font-size: 2em;
        }
        
        .page-number {
            background: #6c757d;
            color: white;
            padding: 5px 15px;
            border-radius: 15px;
            font-size: 0.9em;
        }
        
        .page-controls {
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            border-top: 1px solid #dee2e6;
        }
        
        .page-controls button {
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 0 10px;
            transition: background 0.3s;
        }
        
        .page-controls button:hover:not(:disabled) {
            background: #0056b3;
        }
        
        .page-controls button:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }
        
        .page-indicator {
            margin: 0 20px;
            font-weight: bold;
        }
        
        .error-page {
            text-align: center;
            padding: 50px;
            color: #dc3545;
        }
        
        .error-message {
            margin-top: 15px;
            font-style: italic;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .presentation-header h1 {
                font-size: 2em;
            }
            
            .page-navigation ul {
                flex-direction: column;
            }
            
            .page-header {
                flex-direction: column;
                text-align: center;
                gap: 10px;
            }
            
            .presentation-main {
                padding: 20px;
            }
        }
        """
    
    def _get_multi_page_javascript(self, total_pages: int) -> str:
        """Get JavaScript for multi-page navigation"""
        return f"""
        let currentPage = 1;
        const totalPages = {total_pages};
        
        function showPage(pageNumber) {{
            // Hide all pages
            for (let i = 1; i <= totalPages; i++) {{
                const page = document.getElementById(`page-${{i}}`);
                if (page) {{
                    page.style.display = 'none';
                }}
            }}
            
            // Show selected page
            const targetPage = document.getElementById(`page-${{pageNumber}}`);
            if (targetPage) {{
                targetPage.style.display = 'block';
                currentPage = pageNumber;
                updateControls();
            }}
        }}
        
        function nextPage() {{
            if (currentPage < totalPages) {{
                showPage(currentPage + 1);
            }}
        }}
        
        function previousPage() {{
            if (currentPage > 1) {{
                showPage(currentPage - 1);
            }}
        }}
        
        function updateControls() {{
            const currentPageSpan = document.getElementById('current-page');
            const prevBtn = document.getElementById('prev-btn');
            const nextBtn = document.getElementById('next-btn');
            
            if (currentPageSpan) {{
                currentPageSpan.textContent = currentPage;
            }}
            
            if (prevBtn) {{
                prevBtn.disabled = currentPage === 1;
            }}
            
            if (nextBtn) {{
                nextBtn.disabled = currentPage === totalPages;
            }}
        }}
        
        // Keyboard navigation
        document.addEventListener('keydown', function(event) {{
            if (event.key === 'ArrowLeft') {{
                previousPage();
            }} else if (event.key === 'ArrowRight') {{
                nextPage();
            }}
        }});
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {{
            updateControls();
        }});
        """
    
    def _generate_error_html(self, error_message: str) -> str:
        """Generate error HTML page"""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error - FRESCO Study</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #f8f9fa;
            padding: 50px;
            text-align: center;
        }}
        .error-container {{
            background: white;
            padding: 50px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            max-width: 600px;
            margin: 0 auto;
        }}
        .error-title {{
            color: #dc3545;
            font-size: 2em;
            margin-bottom: 20px;
        }}
        .error-message {{
            color: #6c757d;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1 class="error-title">Processing Error</h1>
        <p class="error-message">Sorry, there was an error processing your request:</p>
        <p class="error-message"><strong>{error_message}</strong></p>
        <p class="error-message">Please try again or contact support if the problem persists.</p>
    </div>
</body>
</html>
        """
    
    def _save_html_to_file(self, html_content: str, filename: str, 
                          page_plan: PagePlan) -> str:
        """
        Save HTML content to file
        
        Args:
            html_content: HTML content to save
            filename: Optional filename
            page_plan: Page plan for naming
            
        Returns:
            Path to saved file
        """
        try:
            # Create output directory
            output_dir = os.path.join(config.html_generator_root, "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                page_suffix = "multipage" if page_plan.is_multi_page else "single"
                filename = f"fresco_{page_suffix}_{timestamp}.html"
            
            if not filename.endswith('.html'):
                filename += '.html'
            
            filepath = os.path.join(output_dir, filename)
            
            # Save file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"HTML saved to: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving HTML: {str(e)}")
            return None
    
    def _build_result_summary(self, user_query: str, page_plan: PagePlan, 
                             page_results: List[PageResult], final_html: str,
                             output_path: str, total_time: float) -> Dict[str, Any]:
        """Build comprehensive result summary"""
        success_count = sum(1 for r in page_results if r.success)
        total_evidence = sum(r.evidence_count for r in page_results)
        
        result = {
            'success': success_count > 0,
            'user_query': user_query,
            'is_multi_page': page_plan.is_multi_page,
            'page_plan': {
                'total_pages': page_plan.total_pages,
                'theme': page_plan.overall_theme,
                'reasoning': page_plan.reasoning
            },
            'pages_processed': len(page_results),
            'pages_successful': success_count,
            'total_evidence_count': total_evidence,
            'output_path': output_path,
            'processing_time': {
                'total': total_time
            },
            'page_details': [
                {
                    'page_number': r.page_info.page_number,
                    'title': r.page_info.title,
                    'success': r.success,
                    'evidence_count': r.evidence_count,
                    'processing_time': r.processing_time,
                    'error': r.error
                }
                for r in page_results
            ]
        }
        
        # Include HTML content
        result['html_content'] = final_html
        
        return result 