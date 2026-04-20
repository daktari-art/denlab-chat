"""Web browsing tool."""
import requests
from bs4 import BeautifulSoup

class BrowserTool:
    """Simple web browser."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "DenLab-Agent/1.0"
        })
    
    def fetch(self, url: str) -> str:
        """Fetch and clean webpage content."""
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Try to find main content
            for selector in ['main', 'article', '[role="main"]', '.content', '#content']:
                main = soup.select_one(selector)
                if main:
                    return main.get_text(separator='\n', strip=True)[:5000]
            
            # Fallback to body
            body = soup.find('body')
            if body:
                return body.get_text(separator='\n', strip=True)[:5000]
            
            return soup.get_text(separator='\n', strip=True)[:5000]
        except Exception as e:
            return f"Browser error: {str(e)}"

_browser = BrowserTool()

def fetch_url(url: str) -> str:
    """Fetch content from a URL."""
    return _browser.fetch(url)
