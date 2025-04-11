from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup
import re

class MainContentExtractor:
    """Extract main content from HTML pages."""
    
    def __init__(self):
        self.content_tags = ['article', 'main', 'div', 'section']
        self.noise_classes = ['header', 'footer', 'nav', 'sidebar', 'menu', 'ad', 'advertisement']
    
    def extract(self, html: str) -> str:
        """Extract the main content from an HTML string."""
        if not html:
            return ""
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style']):
            element.decompose()
            
        # Try to find main content container
        main_content = None
        
        # First try explicit content tags
        for tag in self.content_tags:
            elements = soup.find_all(tag)
            if elements:
                # Find the element with the most text content
                main_content = max(elements, key=lambda x: len(x.get_text()))
                break
                
        if not main_content:
            # Fallback to largest text block
            paragraphs = soup.find_all('p')
            if paragraphs:
                main_content = max(paragraphs, key=lambda x: len(x.get_text()))
                
        if not main_content:
            return ""
            
        # Remove noise elements
        for element in main_content.find_all(class_=self.noise_classes):
            element.decompose()
            
        # Get text content
        text = main_content.get_text()
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text 