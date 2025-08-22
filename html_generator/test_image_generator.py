#!/usr/bin/env python3
"""
Test script for ImageGeneratorChain using real evidence data
Tests image analysis, template matching, and HTML generation
"""

import json
import sys
import os
from typing import List, Dict, Any

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.image_generator import ImageGeneratorChain
from config import config

def load_evidence_data(json_path: str) -> List[Dict[str, Any]]:
    """Load evidence data from JSON file"""
    print(f"📂 Loading evidence data from: {json_path}")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        evidence_results = data.get('evidence_results', [])
        query_info = data.get('query_info', {})
        
        print(f"✅ Loaded {len(evidence_results)} evidence items")
        print(f"📝 Original query: {query_info.get('original_query', 'Unknown')}")
        
        return evidence_results, query_info
        
    except Exception as e:
        print(f"❌ Failed to load evidence data: {e}")
        return [], {}

def print_evidence_summary(evidence_results: List[Dict[str, Any]]):
    """Print summary of evidence data"""
    print("\n" + "="*60)
    print("📊 EVIDENCE SUMMARY")
    print("="*60)
    
    # Count by type
    type_counts = {}
    image_count = 0
    
    for evidence in evidence_results:
        etype = evidence.get('type', 'unknown')
        category = evidence.get('category', 'unknown')
        
        type_counts[etype] = type_counts.get(etype, 0) + 1
        
        if etype == 'image':
            image_count += 1
            print(f"🖼️  Image found: {evidence.get('id')} - {evidence.get('content', '')[:100]}...")
    
    print(f"\nType distribution:")
    for etype, count in sorted(type_counts.items()):
        print(f"  {etype}: {count}")
    
    print(f"\n📸 Total images: {image_count}")

def test_image_analysis(img_gen: ImageGeneratorChain, user_query: str, evidence_results: List[Dict[str, Any]]):
    """Test image analysis functionality"""
    print("\n" + "="*60)
    print("🔍 TESTING IMAGE ANALYSIS")
    print("="*60)
    
    # Filter image evidences
    image_evidences = [e for e in evidence_results if e.get('type') == 'image']
    
    if not image_evidences:
        print("❌ No image evidences found in the data")
        return []
    
    print(f"Found {len(image_evidences)} image evidences to analyze")
    
    analyses = []
    for i, image_evidence in enumerate(image_evidences, 1):
        print(f"\n--- Analyzing Image {i} ---")
        print(f"ID: {image_evidence.get('id')}")
        print(f"Content: {image_evidence.get('content', '')[:200]}...")
        print(f"Original path: {image_evidence.get('original_content', 'N/A')}")
        
        # Test single image analysis
        try:
            analysis = img_gen._analyze_single_image(user_query, image_evidence)
            analyses.append(analysis)
            
            print(f"✅ Analysis completed:")
            print(f"  Relevant features: {analysis.get('has_relevant_features', False)}")
            print(f"  Chart type: {analysis.get('chart_type', 'unknown')}")
            print(f"  Clinical data: {analysis.get('clinical_data_type', 'unknown')}")
            print(f"  Generation needed: {analysis.get('generation_needed', False)}")
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            
    return analyses

def test_template_matching(img_gen: ImageGeneratorChain, user_query: str, analyses: List[Dict[str, Any]]):
    """Test template matching functionality"""
    print("\n" + "="*60)
    print("🎨 TESTING TEMPLATE MATCHING")
    print("="*60)
    
    print(f"Query: '{user_query}'")
    
    # Test template selection
    template_image = img_gen._select_template_image(user_query, analyses)
    
    if template_image:
        print(f"✅ Template matched: {os.path.basename(template_image)}")
        print(f"   Full path: {template_image}")
        print(f"   Exists: {os.path.exists(template_image)}")
    else:
        print("❌ No template matched")
    
    return template_image

def test_generation_decision(img_gen: ImageGeneratorChain, analyses: List[Dict[str, Any]]):
    """Test image generation decision logic"""
    print("\n" + "="*60)
    print("🤖 TESTING GENERATION DECISION")
    print("="*60)
    
    should_generate = img_gen._should_generate_images(analyses)
    
    print(f"Should generate images: {should_generate}")
    
    if analyses:
        print("\nDetailed analysis:")
        for i, analysis in enumerate(analyses, 1):
            print(f"  Image {i}:")
            print(f"    Relevant: {analysis.get('has_relevant_features', False)}")
            print(f"    Generation needed: {analysis.get('generation_needed', False)}")
    
    return should_generate

def test_html_generation(img_gen: ImageGeneratorChain, analyses: List[Dict[str, Any]]):
    """Test HTML reference generation"""
    print("\n" + "="*60)
    print("🌐 TESTING HTML GENERATION")
    print("="*60)
    
    # Test HTML reference creation
    html_refs = img_gen._create_html_image_references(analyses)
    
    print(f"Generated {len(html_refs)} HTML references")
    
    for i, html_ref in enumerate(html_refs, 1):
        print(f"\n--- HTML Reference {i} ---")
        print(html_ref[:300] + "..." if len(html_ref) > 300 else html_ref)
    
    return html_refs

def test_complete_flow(img_gen: ImageGeneratorChain, user_query: str, evidence_results: List[Dict[str, Any]]):
    """Test the complete image processing flow"""
    print("\n" + "="*60)
    print("🚀 TESTING COMPLETE FLOW")
    print("="*60)
    
    try:
        result = img_gen.process_images(user_query, evidence_results)
        
        print("✅ Complete flow executed successfully!")
        print(f"\nResults:")
        print(f"  Has images: {result.get('has_images', False)}")
        print(f"  Image count: {result.get('image_count', 0)}")
        print(f"  Relevant images: {result.get('relevant_images', 0)}")
        print(f"  Should generate: {result.get('should_generate', False)}")
        print(f"  Template used: {result.get('template_used', 'None')}")
        print(f"  Generated images: {len(result.get('generated_images', []))}")
        print(f"  HTML references: {len(result.get('html_image_references', []))}")
        
        return result
        
    except Exception as e:
        print(f"❌ Complete flow failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main test function"""
    print("🧪 ImageGeneratorChain Test Suite")
    print("=" * 80)
    
    # Load evidence data
    evidence_file = "output/evidence_analyze_the_efficacy_OS_20250821_181658.json"
    evidence_results, query_info = load_evidence_data(evidence_file)
    
    if not evidence_results:
        print("❌ No evidence data loaded. Exiting.")
        return
    
    # Print evidence summary
    print_evidence_summary(evidence_results)
    
    # Initialize ImageGeneratorChain
    print("\n" + "="*60)
    print("🔧 INITIALIZING IMAGE GENERATOR")
    print("="*60)
    
    try:
        img_gen = ImageGeneratorChain()
        print("✅ ImageGeneratorChain initialized successfully")
        print(f"   Vision model: {img_gen.vision_llm.model_name}")
        print(f"   Generation model: {img_gen.image_gen_llm.model_name}")
    except Exception as e:
        print(f"❌ Failed to initialize ImageGeneratorChain: {e}")
        return
    
    # Get user query
    user_query = query_info.get('original_query', 'analyze the efficacy OS')
    print(f"\n🔍 Testing with query: '{user_query}'")
    
    # Run individual tests
    analyses = test_image_analysis(img_gen, user_query, evidence_results)
    template_image = test_template_matching(img_gen, user_query, analyses)
    should_generate = test_generation_decision(img_gen, analyses)
    html_refs = test_html_generation(img_gen, analyses)
    
    # Run complete flow test
    complete_result = test_complete_flow(img_gen, user_query, evidence_results)
    
    # Final summary
    print("\n" + "="*80)
    print("📋 TEST SUMMARY")
    print("="*80)
    print(f"✅ Evidence loaded: {len(evidence_results)} items")
    print(f"✅ Image analyses: {len(analyses)} completed")
    print(f"✅ Template matching: {'Found' if template_image else 'None'}")
    print(f"✅ Generation decision: {'Yes' if should_generate else 'No'}")
    print(f"✅ HTML references: {len(html_refs)} generated")
    print(f"✅ Complete flow: {'Success' if complete_result else 'Failed'}")
    
    if complete_result:
        print(f"\n🎯 Final Result Summary:")
        print(f"   Images processed: {complete_result.get('image_count', 0)}")
        print(f"   Relevant for display: {complete_result.get('relevant_images', 0)}")
        print(f"   Ready for HTML: {'Yes' if complete_result.get('html_image_references') else 'No'}")

if __name__ == "__main__":
    main() 