#!/usr/bin/env python3
"""
Main entry point for FRESCO HTML Generator
Supports single-page and multi-page HTML generation
"""

import argparse
import time
import json
import os
import sys

# Add the html_generator directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_orchestrator import EnhancedFrescoOrchestrator
from multi_page_orchestrator import MultiPageOrchestrator
from orchestrator import FrescoHTMLOrchestrator
from config import config

def print_results_summary(result):
    """Print a comprehensive summary of the processing results"""
    print("\n" + "="*80)
    print("📋 PROCESSING RESULTS SUMMARY")
    print("="*80)
    
    if not result.get('success', False):
        print("❌ Processing Failed")
        if result.get('error'):
            print(f"🔥 Error: {result['error']}")
        return
    
    print("✅ Processing Successful")
    
    if result.get('processing_time'):
        total_time = result['processing_time'].get('total', 0)
        print(f"⏱️  Total Time: {total_time:.2f} seconds")
        
    print(f"📝 Original Query: {result['user_query']}")
        
    # Multi-page information
    is_multi_page = result.get('is_multi_page', False)
    orchestrator_used = result.get('orchestrator_used', 'unknown')
    
    if is_multi_page:
        page_plan = result.get('page_plan', {})
        pages_successful = result.get('pages_successful', 0)
        pages_processed = result.get('pages_processed', 0)
        
        print(f"📄 Processing Mode: Multi-page ({pages_successful}/{pages_processed} pages successful)")
        print(f"🎯 Theme: {page_plan.get('theme', 'N/A')}")
        print(f"📊 Evidence Found: {result.get('total_evidence_count', 0)}")
        
        # Page details
        page_details = result.get('page_details', [])
        if page_details:
            print(f"\n📋 Page Breakdown:")
            for page in page_details:
                status = "✅" if page['success'] else "❌"
                print(f"   {status} Page {page['page_number']}: {page['title']} ({page['evidence_count']} evidence)")
    else:
        expanded_queries = result.get('expanded_queries', [])
        print(f"📄 Processing Mode: Single-page")
        print(f"🔍 Query Variations: {len(expanded_queries) if expanded_queries else 0}")
        print(f"📊 Evidence Found: {result.get('evidence_count', 0)}")
    
    print(f"🔧 Orchestrator Used: {orchestrator_used}")
    
    if result.get('output_path'):
        print(f"💾 HTML Saved: {result['output_path']}")
        
    if result.get('evidence_path'):
        print(f"📄 Evidence Saved: {result['evidence_path']}")
        
    print("="*80)


def run_interactive_mode():
    """Run in interactive mode"""
    print("🚀 FRESCO HTML Generator - Interactive Mode")
    print("Type 'quit' to exit")
    print("Type 'switch' to change orchestrator")
    print("Type 'status' to check system status")
    print("-" * 50)
    
    # Default orchestrator
    orchestrator_type = 'enhanced'
    orchestrator = EnhancedFrescoOrchestrator()
    
    while True:
        try:
            user_input = input(f"\n[{orchestrator_type}] 💬 Ask me anything: ").strip()
            
            if user_input.lower() == 'quit':
                print("👋 Goodbye!")
                break
            
            if user_input.lower() == 'switch':
                print("\nSelect orchestrator:")
                print("1. Enhanced (automatic single/multi-page)")
                print("2. Single-page only")  
                print("3. Multi-page only")
                
                choice = input("Enter choice (1-3): ").strip()
                if choice == '1':
                    orchestrator_type = 'enhanced'
                    orchestrator = EnhancedFrescoOrchestrator()
                elif choice == '2':
                    orchestrator_type = 'single'
                    orchestrator = FrescoHTMLOrchestrator()
                elif choice == '3':
                    orchestrator_type = 'multi'
                    orchestrator = MultiPageOrchestrator()
                continue
            
            if user_input.lower() == 'status':
                if hasattr(orchestrator, 'get_system_status'):
                    status = orchestrator.get_system_status()
                    print("\n📊 System Status:")
                    print(json.dumps(status, indent=2))
                else:
                    print("\n📊 Status not available for this orchestrator type")
                continue
            
            if not user_input:
                print("Please enter a question or 'quit' to exit.")
                continue
            
            print(f"\n🔄 Processing: {user_input}")
            result = orchestrator.process_query(user_input)
            
            print_results_summary(result)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            continue


def run_single_query(query: str, output_file: str = None, detailed: bool = False,
                    orchestrator_type: str = 'enhanced', force_mode: str = None):
    """Run a single query and generate HTML"""
    print(f"🔄 Processing single query with {orchestrator_type} orchestrator: {query}")
    
    try:
        # Initialize orchestrator
        if orchestrator_type == 'enhanced':
            orchestrator = EnhancedFrescoOrchestrator()
        elif orchestrator_type == 'single':
            orchestrator = FrescoHTMLOrchestrator()
        elif orchestrator_type == 'multi':
            orchestrator = MultiPageOrchestrator()
        else:
            raise ValueError(f"Unknown orchestrator type: {orchestrator_type}")
        
        # Process the query based on mode
        if detailed and hasattr(orchestrator, 'process_query_steps'):
            # Use detailed step-by-step processing if available
            result = orchestrator.process_query_steps(query, save_html=True, filename=output_file)
            
            # Print detailed step information
            print("\n🔍 Detailed Processing Steps:")
            steps = result.get('steps', {})
            
            # Query processing  
            query_processing = steps.get('query_processing', {})
            print(f"\n📝 Query Processing: {query_processing.get('original_query', query)}")
            if query_processing.get('expanded_queries'):
                for i, exp_query in enumerate(query_processing['expanded_queries'][:3], 1):
                    print(f"   {i}. {exp_query}")
            
            # Search results
            search = steps.get('search', {})
            print(f"\n🔍 Search Results: {search.get('total_evidence', 0)} evidence found")
            summary = search.get('evidence_summary', {})
            if summary:
                print("   Evidence types:")
                for etype, count in summary.get('type_distribution', {}).items():
                    print(f"     {etype}: {count}")
            
            # HTML generation
            html_gen = result['steps'].get('html_generation', {})
            print(f"\n🎨 HTML Generation: {html_gen.get('title', 'Generated')}")
            
        else:
            # Regular processing with force mode support
            if orchestrator_type == 'enhanced' and force_mode:
                if force_mode == 'single':
                    result = orchestrator.force_single_page_processing(
                        query, save_html=True, filename=output_file
                    )
                elif force_mode == 'multi':
                    result = orchestrator.force_multi_page_processing(
                        query, save_html=True, filename=output_file
                    )
                else:
                    result = orchestrator.process_query(
                        query, save_html=True, filename=output_file
                    )
            else:
                if orchestrator_type == 'enhanced':
                    result = orchestrator.process_query(
                        query, save_html=True, filename=output_file
                    )
                else:
                    result = orchestrator.process_query(
                        query, save_html=True, filename=output_file
                    )
            
            print_results_summary(result)
        
        return result
        
    except Exception as e:
        print(f"❌ Error processing query: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='FRESCO HTML Generator - Convert queries to medical presentation HTML',
        epilog='''
Examples:
  %(prog)s                                           # Interactive mode
  %(prog)s --query "FRESCO trial efficacy"          # Generate HTML report
  %(prog)s --query "3-page overview"                # Generate HTML output
  %(prog)s --query "efficacy and safety" --output report.html  # Multi-page HTML
  %(prog)s --interactive                            # Force interactive mode
  %(prog)s --orchestrator multi --query "analysis" # Force multi-page processing
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--query', '-q',
        type=str,
        help='Query to process'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str, 
        help='Output file path'
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Run in interactive mode'
    )
    
    parser.add_argument(
        '--detailed', '-d',
        action='store_true',
        help='Show detailed processing steps'
    )
    
    parser.add_argument(
        '--orchestrator',
        choices=['enhanced', 'single', 'multi'],
        default='enhanced',
        help='Orchestrator type: enhanced (auto), single, or multi (default: enhanced)'
    )
    
    parser.add_argument(
        '--force-mode',
        choices=['single', 'multi'],
        help='Force processing mode for enhanced orchestrator'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    import logging
    log_level = logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Print configuration info
    print("🔧 FRESCO HTML Generator Configuration")
    print(f"   LLM Model: {config.llm_model}")
    print(f"   Project Root: {config.project_root}")
    print(f"   Output Directory: {config.output_dir}")
    print(f"   Top K Results: {config.top_k_results}")
    print("-" * 50)
    
    try:
        if args.interactive or (not args.query):
            run_interactive_mode()
        else:
            result = run_single_query(
                args.query, 
                args.output, 
                args.detailed,
                args.orchestrator,
                args.force_mode
            )
            
            if result.get('success', False):
                sys.exit(0)
            else:
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 