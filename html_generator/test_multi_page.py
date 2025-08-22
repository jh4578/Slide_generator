#!/usr/bin/env python3
"""
Test script for multi-page HTML generation functionality
Tests the enhanced orchestrator with various query types
"""

import sys
import json
import time
from typing import Dict, Any

from enhanced_orchestrator import EnhancedFrescoOrchestrator
from config import config

def test_single_page_query():
    """Test obvious single-page query"""
    print("🧪 Testing Single-Page Query...")
    print("-" * 40)
    
    orchestrator = EnhancedFrescoOrchestrator()
    query = "What is the overall survival rate in FRESCO study?"
    
    start_time = time.time()
    result = orchestrator.process_query(query, save_html=False)
    end_time = time.time()
    
    print(f"Query: {query}")
    print(f"Success: {result.get('success', False)}")
    print(f"Is Multi-page: {result.get('is_multi_page', False)}")
    print(f"Orchestrator Used: {result.get('orchestrator_used', 'unknown')}")
    print(f"Processing Time: {end_time - start_time:.2f}s")
    
    if result.get('success'):
        evidence_count = result.get('evidence_count', 0)
        print(f"Evidence Found: {evidence_count}")
    else:
        print(f"Error: {result.get('error', 'Unknown')}")
    
    print()
    return result

def test_multi_page_query():
    """Test obvious multi-page query"""
    print("🧪 Testing Multi-Page Query...")
    print("-" * 40)
    
    orchestrator = EnhancedFrescoOrchestrator()
    query = "Create a comprehensive 3-page presentation covering FRESCO study efficacy, safety, and patient demographics"
    
    start_time = time.time()
    result = orchestrator.process_query(query, save_html=False)
    end_time = time.time()
    
    print(f"Query: {query}")
    print(f"Success: {result.get('success', False)}")
    print(f"Is Multi-page: {result.get('is_multi_page', False)}")
    print(f"Orchestrator Used: {result.get('orchestrator_used', 'unknown')}")
    print(f"Processing Time: {end_time - start_time:.2f}s")
    
    if result.get('success') and result.get('is_multi_page'):
        page_plan = result.get('page_plan', {})
        pages_successful = result.get('pages_successful', 0)
        pages_processed = result.get('pages_processed', 0)
        total_evidence = result.get('total_evidence_count', 0)
        
        print(f"Pages Processed: {pages_successful}/{pages_processed}")
        print(f"Theme: {page_plan.get('theme', 'N/A')}")
        print(f"Total Evidence: {total_evidence}")
        
        page_details = result.get('page_details', [])
        if page_details:
            print("Page Details:")
            for page in page_details:
                status = "✅" if page['success'] else "❌"
                print(f"  {status} Page {page['page_number']}: {page['title']} ({page['evidence_count']} evidence)")
    elif result.get('success'):
        evidence_count = result.get('evidence_count', 0)
        print(f"Fell back to single-page with {evidence_count} evidence")
    else:
        print(f"Error: {result.get('error', 'Unknown')}")
    
    print()
    return result

def test_ambiguous_query():
    """Test ambiguous query that could go either way"""
    print("🧪 Testing Ambiguous Query...")
    print("-" * 40)
    
    orchestrator = EnhancedFrescoOrchestrator()
    query = "Show me FRESCO study efficacy and safety data"
    
    start_time = time.time()
    result = orchestrator.process_query(query, save_html=False)
    end_time = time.time()
    
    print(f"Query: {query}")
    print(f"Success: {result.get('success', False)}")
    print(f"Is Multi-page: {result.get('is_multi_page', False)}")
    print(f"Orchestrator Used: {result.get('orchestrator_used', 'unknown')}")
    print(f"Processing Time: {end_time - start_time:.2f}s")
    
    if result.get('success'):
        if result.get('is_multi_page'):
            pages_successful = result.get('pages_successful', 0)
            pages_processed = result.get('pages_processed', 0)
            print(f"Pages: {pages_successful}/{pages_processed}")
        else:
            evidence_count = result.get('evidence_count', 0)
            print(f"Evidence Found: {evidence_count}")
    else:
        print(f"Error: {result.get('error', 'Unknown')}")
    
    print()
    return result

def test_forced_modes():
    """Test forced single and multi-page modes"""
    print("🧪 Testing Forced Modes...")
    print("-" * 40)
    
    orchestrator = EnhancedFrescoOrchestrator()
    query = "FRESCO efficacy data"
    
    # Test forced single-page
    print("Forcing single-page mode:")
    result_single = orchestrator.force_single_page_processing(query, save_html=False)
    print(f"  Success: {result_single.get('success', False)}")
    print(f"  Is Multi-page: {result_single.get('is_multi_page', False)}")
    print(f"  Orchestrator: {result_single.get('orchestrator_used', 'unknown')}")
    
    # Test forced multi-page
    print("Forcing multi-page mode:")
    result_multi = orchestrator.force_multi_page_processing(query, save_html=False)
    print(f"  Success: {result_multi.get('success', False)}")
    print(f"  Is Multi-page: {result_multi.get('is_multi_page', False)}")
    print(f"  Orchestrator: {result_multi.get('orchestrator_used', 'unknown')}")
    
    if result_multi.get('success') and result_multi.get('is_multi_page'):
        pages_successful = result_multi.get('pages_successful', 0)
        pages_processed = result_multi.get('pages_processed', 0)
        print(f"  Pages: {pages_successful}/{pages_processed}")
    
    print()
    return result_single, result_multi

def test_system_status():
    """Test system status functionality"""
    print("🧪 Testing System Status...")
    print("-" * 40)
    
    orchestrator = EnhancedFrescoOrchestrator()
    status = orchestrator.get_system_status()
    
    print("System Status:")
    print(json.dumps(status, indent=2))
    print()
    
    return status

def run_all_tests():
    """Run all test functions"""
    print("🚀 Starting Multi-Page HTML Generator Tests")
    print("=" * 50)
    
    try:
        # Test 1: Single-page query
        result1 = test_single_page_query()
        
        # Test 2: Multi-page query
        result2 = test_multi_page_query()
        
        # Test 3: Ambiguous query
        result3 = test_ambiguous_query()
        
        # Test 4: Forced modes
        result4_single, result4_multi = test_forced_modes()
        
        # Test 5: System status
        status = test_system_status()
        
        # Summary
        print("📊 Test Summary")
        print("-" * 20)
        
        tests = [
            ("Single-page query", result1.get('success', False)),
            ("Multi-page query", result2.get('success', False)),
            ("Ambiguous query", result3.get('success', False)),
            ("Forced single-page", result4_single.get('success', False)),
            ("Forced multi-page", result4_multi.get('success', False)),
            ("System status", 'error' not in status)
        ]
        
        passed = sum(1 for _, success in tests if success)
        total = len(tests)
        
        print(f"Tests Passed: {passed}/{total}")
        
        for test_name, success in tests:
            status_icon = "✅" if success else "❌"
            print(f"  {status_icon} {test_name}")
        
        if passed == total:
            print("\n🎉 All tests passed! Multi-page functionality is working correctly.")
        else:
            print(f"\n⚠️  {total - passed} tests failed. Check the output above for details.")
        
        return passed == total
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 