#!/usr/bin/env python3
"""
简化测试 - 直接使用图片路径生成HTML内容
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chains.html_generator import HTMLGeneratorChain

def test_simplified_html_generation():
    """测试简化的HTML生成流程"""
    
    print("🚀 开始简化HTML生成测试...")
    
    # 初始化HTML生成器
    html_generator = HTMLGeneratorChain()
    
    # 测试查询
    test_query = "analyze the efficacy overall survival"
    
    # 模拟证据数据
    test_evidence = [
        {
            "content": "Fruquintinib demonstrated significant improvement in overall survival (OS) with a median OS of 9.3 months vs 6.6 months (HR=0.66, 95% CI: 0.51-0.86, p<0.001)",
            "source": "FRESCO-2 Study",
            "relevance_score": 0.95
        },
        {
            "content": "The safety profile was consistent with previous studies, with hand-foot syndrome being the most common adverse event",
            "source": "Safety Analysis",
            "relevance_score": 0.85
        }
    ]
    
    # 简化的图片结果 - 直接提供图片路径
    test_image_results = {
        "has_images": True,
        "should_generate": False,
        "image_count": 1,
        "html_image_references": [
            '''<div class="evidence-image">
                <img src="efficacy_os.png" 
                     alt="Clinical chart" 
                     class="clinical-chart">
                <p class="image-caption">
                    Clinical data visualization
                </p>
            </div>'''
        ]
    }
    
    # 生成HTML内容
    print("\n📝 生成HTML内容...")
    
    # 调试：显示图片信息
    image_info = html_generator._prepare_image_info(test_image_results)
    image_html_content = html_generator._prepare_image_html_content(test_image_results)
    
    print(f"\n🖼️  调试信息 - 图片摘要:")
    print(image_info)
    print(f"\n🖼️  调试信息 - 图片HTML内容:")
    print(repr(image_html_content))
    
    content_result = html_generator.generate_html_content(
        test_query,
        test_evidence, 
        test_image_results
    )
    
    print(f"✅ 内容生成结果:")
    print(f"   标题: {content_result.get('title', 'N/A')}")
    print(f"   HTML长度: {len(content_result.get('html_content', ''))}")
    print(f"   摘要: {content_result.get('summary', 'N/A')}")
    
    # 生成完整HTML
    print("\n🎨 生成完整HTML...")
    html_content = html_generator.create_complete_html(
        test_query,
        test_evidence, 
        test_image_results
    )
    
    # 保存结果
    output_file = html_generator.save_html_to_file(
        html_content,
        "simplified_output.html"
    )
    
    print(f"\n✅ HTML生成成功: {output_file}")
    
    # 验证关键功能
    print("\n🔍 验证结果:")
    
    # 检查图片引用
    if "efficacy_os.png" in html_content:
        print("✓ 图片路径已正确包含")
    else:
        print("✗ 图片路径未找到")
    
    # 检查模板结构
    if "ai-content" in html_content:
        print("✓ 模板结构已保持")
    else:
        print("✗ 模板结构缺失")
    
    # 检查内容
    if content_result.get('title'):
        print("✓ 标题生成成功")
    else:
        print("✗ 标题生成失败")
    
    print(f"\n🎯 测试完成! 输出文件: {output_file}")

if __name__ == "__main__":
    test_simplified_html_generation() 