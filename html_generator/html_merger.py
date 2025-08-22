#!/usr/bin/env python3
"""
Enhanced HTML Merger for combining multiple HTML pages into a single scrollable document
Based on the improved merge script provided, handles CSS/JS merging and deduplication
"""
import logging
import hashlib
import re
from typing import List, Tuple
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class HTMLMerger:
    """Enhanced HTML页面合并器"""
    
    # CSS patterns that prevent scrolling
    NO_SCROLL_PATTERNS = [
        (r"overflow\s*:\s*hidden\s*;", "overflow: auto;"),
        (r"height\s*:\s*100vh\s*;", "height: auto;"),
        (r"max-height\s*:\s*calc\(\s*100vh\s*-\s*[^)]+\)\s*;", "max-height: none;"),
        (r"min-height\s*:\s*calc\(\s*100vh\s*-\s*[^)]+\)\s*;", "min-height: auto;"),
    ]
    
    # CSS to force scrollability
    FORCE_SCROLL_CSS = """
/* Enhanced HTML Merger: force page to be scrollable */
html, body {
    height: auto !important;
    overflow: auto !important;
}

/* Normalize fixed containers */
*[style*="overflow: hidden"] { 
    overflow: auto !important; 
}
*[style*="height: 100vh"] { 
    height: auto !important; 
}

/* Multi-page layout styles */
.merged-page-container {
    max-width: 1440px;
    margin: 0 auto;
    padding: 20px;
}

.merged-page-section {
    margin: 30px 0;
    padding: 20px 0;
}

.merged-page-section:not(:last-child) {
    border-bottom: 2px solid #e5e7eb;
    padding-bottom: 40px;
}

.merged-page-title {
    font-size: 24px;
    font-weight: bold;
    margin: 0 0 20px 0;
    padding: 15px 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.merged-page-content {
    position: relative;
}

/* Ensure main containers are not fixed height */
.main {
    height: auto !important;
    max-height: none !important;
    min-height: auto !important;
    overflow: visible !important;
}
"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def merge_html_pages(self, html_contents: List[str], overall_theme: str = "") -> str:
        """
        将多个HTML页面合并成一个可滚动的HTML文档 - 增强版
        
        Args:
            html_contents: HTML内容列表
            overall_theme: 整体主题（可选）
            
        Returns:
            合并后的HTML字符串
        """
        if not html_contents:
            raise ValueError("HTML内容列表不能为空")
            
        if len(html_contents) == 1:
            return self._make_scrollable(html_contents[0])
        
        self.logger.info(f"开始合并 {len(html_contents)} 个HTML页面...")
        
        try:
            all_styles = []
            all_links = []
            all_scripts = []
            page_sections = []
            
            # 处理每个HTML页面
            for i, html_content in enumerate(html_contents, 1):
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 提取head内容
                styles, links, scripts = self._extract_head_content(soup)
                all_styles.extend(styles)
                all_links.extend(links)
                all_scripts.extend(scripts)
                
                # 提取body内容
                section_html = self._extract_body_content(soup, i)
                
                # 创建页面区块 - 不添加额外的页面标题
                section = f'''
                <div class="merged-page-section" id="page-{i}">
                    <div class="merged-page-content">
                        {section_html}
                    </div>
                </div>
                '''
                page_sections.append(section)
            
            # 去重head内容
            dedup_styles = self._dedupe_styles(all_styles)
            dedup_links = self._dedupe_links(all_links)
            dedup_scripts = self._dedupe_scripts(all_scripts)
            
            # 构建最终HTML
            final_html = self._build_final_html(
                dedup_styles, dedup_links, dedup_scripts, 
                page_sections, overall_theme
            )
            
            self.logger.info(f"成功合并 {len(html_contents)} 个HTML页面")
            return final_html
            
        except Exception as e:
            self.logger.error(f"合并页面时出错: {str(e)}")
            # 使用简单fallback
            return self._simple_merge_fallback(html_contents, overall_theme)
    
    def _extract_head_content(self, soup: BeautifulSoup) -> Tuple[List[str], List[str], List[Tuple]]:
        """提取HTML head中的样式、链接和脚本"""
        styles = []
        links = []
        scripts = []
        
        if not soup.head:
            return styles, links, scripts
            
        # 提取<style>标签
        for style_tag in soup.head.find_all('style'):
            if style_tag.string and style_tag.string.strip():
                cleaned_css = self._clean_no_scroll_css(style_tag.string)
                styles.append(cleaned_css)
        
        # 提取<link rel="stylesheet">
        for link_tag in soup.head.find_all('link'):
            rel = link_tag.get('rel', [])
            if isinstance(rel, list):
                rel = [r.lower() for r in rel]
            else:
                rel = [str(rel).lower()]
            if 'stylesheet' in rel and link_tag.get('href'):
                links.append(str(link_tag))
        
        # 提取<script>标签
        for script_tag in soup.head.find_all('script'):
            if script_tag.get('src'):
                scripts.append(('external', script_tag.get('src'), str(script_tag)))
            else:
                code = script_tag.string or ""
                if code.strip():
                    scripts.append(('inline', code, str(script_tag)))
        
        return styles, links, scripts
    
    def _extract_body_content(self, soup: BeautifulSoup, page_num: int) -> str:
        """提取body内容"""
        if soup.body:
            # 创建body副本以避免修改原始内容
            body_clone = BeautifulSoup(str(soup.body), 'html.parser')
            body_inner = body_clone.body
            if body_inner:
                # 可选：为元素ID添加前缀以避免冲突
                self._prefix_ids(body_inner, f"p{page_num}-")
                return body_inner.decode_contents()
        
        # fallback: 如果没有body，使用整个文档
        self._prefix_ids(soup, f"p{page_num}-")
        return soup.decode_contents()
    
    def _prefix_ids(self, soup: BeautifulSoup, prefix: str):
        """为元素ID添加前缀以避免冲突"""
        for element in soup.find_all(id=True):
            element['id'] = f"{prefix}{element['id']}"
    
    def _clean_no_scroll_css(self, css_text: str) -> str:
        """清理阻止滚动的CSS规则"""
        if not css_text:
            return css_text
        
        result = css_text
        for pattern, replacement in self.NO_SCROLL_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    def _sha256(self, text: str) -> str:
        """计算字符串的SHA256哈希"""
        return hashlib.sha256(text.encode('utf-8', errors='ignore')).hexdigest()
    
    def _dedupe_styles(self, styles: List[str]) -> List[str]:
        """去重CSS样式"""
        seen_hashes = set()
        deduped = []
        
        for style in styles:
            style_hash = self._sha256(style)
            if style_hash not in seen_hashes:
                seen_hashes.add(style_hash)
                deduped.append(style)
        
        return deduped
    
    def _dedupe_links(self, links: List[str]) -> List[str]:
        """去重link标签"""
        seen = set()
        deduped = []
        
        for link in links:
            if link not in seen:
                seen.add(link)
                deduped.append(link)
        
        return deduped
    
    def _dedupe_scripts(self, scripts: List[Tuple]) -> List[Tuple]:
        """去重script标签"""
        seen = set()
        deduped = []
        
        for script_type, payload, raw in scripts:
            if script_type == 'external':
                key = ('external', payload)  # payload是src
            else:
                key = ('inline', self._sha256(payload))  # payload是代码
            
            if key not in seen:
                seen.add(key)
                deduped.append((script_type, payload, raw))
        
        return deduped
    
    def _build_final_html(self, styles: List[str], links: List[str], scripts: List[Tuple], 
                         sections: List[str], title: str = "") -> str:
        """构建最终的HTML文档"""
        
        # 构建head内容
        head_parts = [
            '<meta charset="utf-8">',
            f'<title>{title if title else "Merged Document"}</title>'
        ]
        
        # 添加样式
        for style in styles:
            head_parts.append(f'<style>\n{style}\n</style>')
        
        # 添加强制滚动样式
        head_parts.append(f'<style>\n{self.FORCE_SCROLL_CSS}\n</style>')
        
        # 添加link标签
        head_parts.extend(links)
        
        # 添加script标签
        for script_type, payload, raw in scripts:
            if script_type == 'external':
                head_parts.append(raw)
            else:
                head_parts.append(f'<script>\n{payload}\n</script>')
        
        # 构建body内容
        body_content = '\n'.join(sections)
        
        # 构建完整HTML
        final_html = f"""<!DOCTYPE html>
<html>
<head>
{chr(10).join(head_parts)}
</head>
<body>
<div class="merged-page-container">
{body_content}
</div>
</body>
</html>
"""
        
        return final_html
    
    def _make_scrollable(self, html_content: str) -> str:
        """
        修改单个HTML使其支持滚动
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 修改现有的CSS样式
        styles = soup.find_all('style')
        for style in styles:
            if style.string:
                cleaned_css = self._clean_no_scroll_css(style.string)
                style.string.replace_with(cleaned_css)
        
        # 添加强制滚动样式
        if soup.head:
            scroll_style = soup.new_tag('style')
            scroll_style.string = self.FORCE_SCROLL_CSS
            soup.head.append(scroll_style)
        
        return str(soup)
    
    def _simple_merge_fallback(self, html_contents: List[str], overall_theme: str = "") -> str:
        """
        简单的HTML合并fallback方法
        """
        self.logger.info("使用简单fallback方法合并HTML")
        
        # 提取所有页面的body内容
        all_body_contents = []
        
        for i, html_content in enumerate(html_contents, 1):
            soup = BeautifulSoup(html_content, 'html.parser')
            body = soup.body
            
            if body:
                # 不添加额外的页面标题，直接合并内容
                page_content = f'''
                <div class="merged-page-section" data-page="{i}" style="margin: 30px 0; padding: 20px 0; border-bottom: 2px solid #e0e0e0;">
                    <div class="merged-page-content">
                        {str(body)}
                    </div>
                </div>
                '''
                all_body_contents.append(page_content)
        
        # 构建完整的HTML
        merged_html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{overall_theme if overall_theme else "Merged Pages"}</title>
            <meta charset="utf-8">
            <style>
                {self.FORCE_SCROLL_CSS}
                .merged-page-section:last-child {{
                    border-bottom: none;
                }}
            </style>
        </head>
        <body>
            <div class="merged-page-container">
                {''.join(all_body_contents)}
            </div>
        </body>
        </html>
        '''
        
        return merged_html 