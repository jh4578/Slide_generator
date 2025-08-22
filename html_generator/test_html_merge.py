#!/usr/bin/env python3
"""
Test script for HTML merging functionality
Tests the new HTMLMerger and multi-page processing
"""
import sys
import os

# Add the html_generator directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from html_merger import HTMLMerger

def test_html_merger_simple():
    """Test the HTMLMerger class with existing HTML files"""
    print("🧪 Testing HTMLMerger with existing files...")
    
    # Read existing HTML files
    image_html_path = "output/fresco_presentation_image.html"
    text_html_path = "output/fresco_presentation_text.html"
    
    html_files = []
    for path in [image_html_path, text_html_path]:
        if os.path.exists(path):
            html_files.append(path)
            print(f"✅ Found: {path}")
        else:
            print(f"❌ Not found: {path}")
    
    if len(html_files) < 2:
        print("⚠️  Need at least 2 HTML files to test merging. Let's create simple test files...")
        return test_html_merger_with_sample_files()
    
    try:
        # Read HTML content
        html_contents = []
        for path in html_files:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                html_contents.append(content)
                print(f"📄 Read {path}: {len(content)} characters")
        
        # Create HTMLMerger instance
        merger = HTMLMerger()
        
        # Test merging
        theme = "FRESCO Study Analysis"
        
        print(f"🔄 Merging {len(html_contents)} HTML files...")
        merged_html = merger.merge_html_pages(html_contents, theme)
        print(f"✅ Successfully merged HTML: {len(merged_html)} characters")
        
        # Save merged result
        output_path = "output/test_merged_html.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(merged_html)
        print(f"💾 Saved merged HTML to: {output_path}")
        print(f"🌐 Open in browser: file://{os.path.abspath(output_path)}")
        
        return True
        
    except Exception as e:
        print(f"❌ HTMLMerger test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_html_merger_with_sample_files():
    """Test HTMLMerger with sample HTML content"""
    print("🧪 Testing HTMLMerger with sample HTML content...")
    
    # Create sample HTML content
    sample_html_1 = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page 1 - Efficacy</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .main { width: 1200px; margin: 0 auto; padding: 20px; }
            .header { background: #f0f8ff; padding: 15px; border-radius: 8px; }
            .content { margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="main">
            <div class="header">
                <h1>FRESCO Study Efficacy Analysis</h1>
            </div>
            <div class="content">
                <h2>Primary Endpoint Results</h2>
                <p>The FRESCO study demonstrated significant improvement in progression-free survival...</p>
                <ul>
                    <li>Median PFS: 9.3 months vs 6.1 months (control)</li>
                    <li>Hazard Ratio: 0.43 (95% CI: 0.30-0.62)</li>
                    <li>P-value: <0.001</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    
    sample_html_2 = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page 2 - Safety</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .main { width: 1200px; margin: 0 auto; padding: 20px; }
            .header { background: #fff8dc; padding: 15px; border-radius: 8px; }
            .content { margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="main">
            <div class="header">
                <h1>FRESCO Study Safety Profile</h1>
            </div>
            <div class="content">
                <h2>Adverse Events</h2>
                <p>The safety profile was generally manageable with expected side effects...</p>
                <ul>
                    <li>Grade 3/4 AEs: 45% vs 38% (control)</li>
                    <li>Treatment discontinuation: 12%</li>
                    <li>Most common AEs: diarrhea, fatigue, nausea</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        # Create HTMLMerger instance
        merger = HTMLMerger()
        
        # Test merging
        html_contents = [sample_html_1, sample_html_2]
        theme = "FRESCO Study Analysis"
        
        print(f"🔄 Merging {len(html_contents)} sample HTML pages...")
        merged_html = merger.merge_html_pages(html_contents, theme)
        print(f"✅ Successfully merged HTML: {len(merged_html)} characters")
        
        # Save merged result
        output_path = "output/test_sample_merged.html"
        os.makedirs("output", exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(merged_html)
        print(f"💾 Saved sample merged HTML to: {output_path}")
        print(f"🌐 Open in browser: file://{os.path.abspath(output_path)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sample HTMLMerger test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_multi_page_orchestrator():
    """Test the multi-page orchestrator with HTML merging"""
    print("\n🧪 Testing MultiPageOrchestrator...")
    
    try:
        from multi_page_orchestrator import MultiPageOrchestrator
        
        orchestrator = MultiPageOrchestrator()
        
        # Test query that should generate multiple pages
        test_query = "Create a 2-page presentation covering FRESCO study efficacy and safety profiles"
        
        print(f"🔄 Processing query: {test_query}")
        result = orchestrator.process_query(test_query, save_html=True, filename="test_multipage_merge")
        
        if result.get('success'):
            print("✅ Multi-page orchestrator test PASSED!")
            print(f"📊 Pages processed: {result.get('pages_processed', 0)}")
            print(f"📊 Pages successful: {result.get('pages_successful', 0)}")
            if result.get('output_path'):
                print(f"💾 Output saved to: {result['output_path']}")
                print(f"🌐 Open in browser: file://{os.path.abspath(result['output_path'])}")
            return True
        else:
            print(f"❌ Multi-page orchestrator test failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Multi-page orchestrator test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Starting HTML Merge Tests")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 2
    
    # Test 1: HTMLMerger directly
    print("\n" + "="*60)
    if test_html_merger_simple():
        tests_passed += 1
    
    # Test 2: MultiPageOrchestrator (commented out for now since it requires API)
    # print("\n" + "="*60)
    # if test_multi_page_orchestrator():
    #     tests_passed += 1
    
    print("\n" + "=" * 60)
    print(f"🏁 Tests completed: {tests_passed}/{total_tests} passed")
    
    if tests_passed >= 1:  # At least the basic merge test should pass
        print("🎉 HTML merging functionality is working!")
        return True
    else:
        print("❌ HTML merging tests FAILED!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 