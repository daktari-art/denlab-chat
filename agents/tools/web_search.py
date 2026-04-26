"""Web search capabilities."""
import requests
import json
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

class WebSearchTool:
    """Search and scrape web content."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "DenLab-Agent/1.0 (Research Bot)"
        })
    
    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search using DuckDuckGo Lite (no API key needed)."""
        try:
            url = "https://duckduckgo.com/html/"
            params = {"q": query}
            resp = self.session.get(url, params=params, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            results = []
            for result in soup.select('.result')[:num_results]:
                title_elem = result.select_one('.result__title')
                snippet_elem = result.select_one('.result__snippet')
                url_elem = result.select_one('.result__url')
                
                if title_elem and url_elem:
                    results.append({
                        "title": title_elem.get_text(strip=True),
                        "url": url_elem.get_text(strip=True),
                        "snippet": snippet_elem.get_text(strip=True) if snippet_elem else ""
                    })
            return results
        except Exception as e:
            return [{"error": str(e)}]
    
    def scrape(self, url: str) -> str:
        """Scrape page content."""
        try:
            resp = self.session.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Remove noise
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines[:100])  # Limit length
        except Exception as e:
            return f"Scrape failed: {str(e)}"
    
    def deep_research(self, topic: str, depth: int = 2) -> Dict:
        """Multi-hop research."""
        findings = []
        queries = [topic]
        seen_urls = set()
        
        for _ in range(depth):
            new_queries = []
            for query in queries:
                results = self.search(query, 3)
                for r in results:
                    if 'url' in r and r['url'] not in seen_urls:
                        seen_urls.add(r['url'])
                        content = self.scrape(r['url'])
                        findings.append({
                            "query": query,
                            "source": r['url'],
                            "title": r.get('title', ''),
                            "content": content[:2000]
                        })
            queries = new_queries[:2]
        
        return {
            "topic": topic,
            "total_sources": len(findings),
            "findings": findings
        }

# Convenience functions for registry
_search_tool = WebSearchTool()

def web_search(query: str, num_results: int = 5) -> str:
    """Search the web for information."""
    results = _search_tool.search(query, num_results)
    return json.dumps(results, indent=2)

def deep_research(topic: str, depth: int = 2) -> str:
    """Conduct deep multi-source research."""
    result = _search_tool.deep_research(topic, depth)
    return json.dumps(result, indent=2)
