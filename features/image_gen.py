"""Image generation feature."""
import streamlit as st
from core.api_client import PollinationsClient

class ImageGenerator:
    def __init__(self):
        self.client = PollinationsClient()
        self.ratios = {
            "1:1": (1024, 1024),
            "16:9": (1024, 576),
            "9:16": (576, 1024),
        }
    
    def parse_command(self, text: str) -> dict:
        if not text.lower().startswith('/imagine'):
            return None
        
        prompt = text[8:].strip()
        ratio = "1:1"
        
        # Parse --ar 16:9
        import re
        ar_match = re.search(r'--ar\s+(\d+:\d+)', prompt)
        if ar_match and ar_match.group(1) in self.ratios:
            ratio = ar_match.group(1)
            prompt = re.sub(r'--ar\s+\d+:\d+', '', prompt).strip()
        
        return {"prompt": prompt, "ratio": ratio}
    
    def generate(self, prompt: str, ratio: str = "1:1") -> str:
        w, h = self.ratios.get(ratio, (1024, 1024))
        return self.client.generate_image(prompt, w, h)
