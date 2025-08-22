# Multi-Page HTML Generator Documentation

## Overview

The FRESCO HTML Generator has been enhanced with intelligent multi-page presentation capabilities. The system can now automatically detect when a user query requires multiple pages and generate comprehensive presentations with navigation, while maintaining full backward compatibility with single-page generation.

## Architecture

### Enhanced Components

```
Enhanced Entry Point:
├── EnhancedFrescoOrchestrator (main entry)
│   ├── Auto-detects single vs multi-page needs
│   ├── Provides fallback mechanisms
│   └── Unified API for all query types
│
├── PagePlannerAgent (new)
│   ├── LLM-powered query analysis
│   ├── Intelligent page structure planning
│   └── Validation and fallback logic
│
├── MultiPageOrchestrator (new)
│   ├── Parallel page processing
│   ├── Page combination and navigation
│   └── Multi-page HTML template generation
│
└── FrescoHTMLOrchestrator (existing, unchanged)
    ├── Single-page processing
    ├── Evidence search and generation
    └── Original functionality preserved
```

## Key Features

### 1. Intelligent Query Analysis
- **Automatic Detection**: Uses LLM to analyze user intent
- **Heuristic Optimization**: Quick checks for obvious single-page queries
- **Fallback Protection**: Always falls back to single-page if needed

### 2. Parallel Processing
- **Concurrent Execution**: Multiple pages processed simultaneously
- **Resource Management**: Configurable concurrent page limits
- **Independent Processing**: Each page has its own evidence search

### 3. Enhanced Navigation
- **Interactive UI**: Click-based and keyboard navigation
- **Page Controls**: Previous/Next buttons with state management
- **Responsive Design**: Mobile-friendly multi-page layouts

### 4. Backward Compatibility
- **Seamless Migration**: Existing code works without changes
- **API Consistency**: Same methods and return formats
- **Single-Page Fallback**: Automatic degradation for errors

## Usage Examples

### Basic Usage (Auto-Detection)

```python
from enhanced_orchestrator import EnhancedFrescoOrchestrator

orchestrator = EnhancedFrescoOrchestrator()

# Single-page query (auto-detected)
result = orchestrator.process_query("What is the overall survival rate?")

# Multi-page query (auto-detected) 
result = orchestrator.process_query(
    "Create a 3-page presentation covering efficacy, safety, and demographics"
)
```

### Forced Processing Modes

```python
# Force single-page processing
result = orchestrator.force_single_page_processing(
    "FRESCO study overview",
    save_html=True,
    filename="single_overview.html"
)

# Force multi-page processing
result = orchestrator.force_multi_page_processing(
    "Show me efficacy data",
    save_html=True, 
    filename="multi_efficacy.html"
)
```

### Command Line Interface

```bash
# Enhanced orchestrator with auto-detection (default)
python main.py --query "Create comprehensive FRESCO analysis"

# Force single-page mode with enhanced orchestrator
python main.py --query "efficacy data" --force-mode single

# Force multi-page mode
python main.py --query "show me efficacy" --force-mode multi

# Use specific orchestrator type
python main.py --query "safety data" --orchestrator single
python main.py --query "3-page overview" --orchestrator multi

# Interactive mode with orchestrator switching
python main.py --interactive
```

## Query Analysis Logic

### Multi-Page Indicators
The system looks for these patterns to identify multi-page needs:

- **Explicit mentions**: "3-page presentation", "slides about"
- **Multiple topics**: "efficacy and safety", "overview covering X, Y, Z"
- **Comprehensive requests**: "complete analysis", "full overview"
- **Multiple data types**: "demographics, efficacy, and adverse events"

### Single-Page Indicators
These patterns suggest single-page processing:

- **Specific questions**: "What is the overall survival?"
- **Single topics**: "FRESCO safety data"
- **Simple requests**: "Show me", "Tell me about"
- **Short queries**: 5 words or less

## Configuration

### Environment Variables

```bash
# Multi-page specific settings
MAX_CONCURRENT_PAGES=3          # Max parallel page processing
ENABLE_MULTI_PAGE=true          # Enable/disable multi-page feature
AUTO_PAGE_DETECTION=true        # Enable automatic detection
MAX_PAGES_PER_PRESENTATION=10   # Maximum pages per presentation

# Existing settings (still apply)
OPENAI_API_KEY=your_api_key
LLM_MODEL=gpt-4-turbo-preview
TOP_K_RESULTS=20
```

### Configuration Access

```python
from config import config

# Get multi-page configuration
multi_page_config = config.get_multi_page_config()
print(multi_page_config)
# Output: {
#     'max_concurrent_pages': 3,
#     'enable_multi_page': True,
#     'auto_page_detection': True,
#     'max_pages_per_presentation': 10
# }
```

## Response Format

### Single-Page Response
```json
{
    "success": true,
    "user_query": "What is overall survival?",
    "is_multi_page": false,
    "orchestrator_used": "single_page",
    "evidence_count": 15,
    "html_content": "...",
    "processing_time": {"total": 5.2}
}
```

### Multi-Page Response
```json
{
    "success": true,
    "user_query": "Create 3-page presentation...",
    "is_multi_page": true,
    "orchestrator_used": "multi_page",
    "page_plan": {
        "total_pages": 3,
        "theme": "FRESCO Study Analysis",
        "reasoning": "User requested comprehensive 3-page coverage"
    },
    "pages_processed": 3,
    "pages_successful": 3,
    "total_evidence_count": 45,
    "html_content": "...",
    "page_details": [
        {
            "page_number": 1,
            "title": "Efficacy Data",
            "success": true,
            "evidence_count": 15,
            "processing_time": 4.1
        }
    ]
}
```

## Testing

### Running Tests

```bash
# Run comprehensive test suite
python test_multi_page.py

# Test specific functionality
python main.py --query "test query" --verbose
```

### Test Coverage
- Single-page query detection
- Multi-page query processing  
- Ambiguous query handling
- Forced mode functionality
- System status validation
- Error handling and fallbacks

## Performance Considerations

### Parallel Processing Benefits
- **Speed**: 3-5x faster for multi-page requests
- **Efficiency**: Concurrent evidence search and HTML generation
- **Scalability**: Configurable concurrency limits

### Resource Management
- **Memory**: Each page process has independent memory
- **API Limits**: Distributed across parallel requests
- **Fallback**: Automatic single-page fallback on resource constraints

## Migration Guide

### From Single-Page to Enhanced
```python
# Before (still works)
from orchestrator import FrescoHTMLOrchestrator
orchestrator = FrescoHTMLOrchestrator()

# After (recommended)
from enhanced_orchestrator import EnhancedFrescoOrchestrator  
orchestrator = EnhancedFrescoOrchestrator()

# Same API, enhanced capabilities
result = orchestrator.process_query("your query")
```

### Gradual Migration
1. **Phase 1**: Use Enhanced orchestrator with existing queries
2. **Phase 2**: Test multi-page queries in development
3. **Phase 3**: Enable multi-page in production
4. **Phase 4**: Deprecate direct single/multi orchestrator usage

## Troubleshooting

### Common Issues

1. **Page Planning Fails**
   - **Symptom**: Always falls back to single-page
   - **Solution**: Check LLM model configuration and API limits

2. **Parallel Processing Errors**
   - **Symptom**: Some pages fail in multi-page mode
   - **Solution**: Reduce `MAX_CONCURRENT_PAGES` setting

3. **Memory Issues**
   - **Symptom**: Out of memory errors with many pages
   - **Solution**: Lower concurrency or increase system memory

### Debug Mode
```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use detailed processing
result = orchestrator.process_query_steps("your query")
```

## Future Enhancements

### Planned Features
- **Page Templates**: Specialized templates for different content types
- **Cross-Page References**: Links and references between pages
- **Export Formats**: PDF and PowerPoint export
- **Page Caching**: Cache and reuse page content

### Performance Optimizations
- **Smart Caching**: Reuse evidence across similar pages
- **Lazy Loading**: Load page content on demand
- **Compression**: Optimize HTML output size

## Support

For questions or issues with multi-page functionality:

1. Check this documentation
2. Run the test suite: `python test_multi_page.py`
3. Enable verbose logging for debugging
4. Review configuration settings
5. Test with simplified queries first 