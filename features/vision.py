"""Vision capabilities - analyze uploaded images."""
import base64
import streamlit as st
from core.api_client import get_client
from typing import Optional

class VisionAnalyzer:
    def __init__(self):
        self.client = get_client()
        self.vision_models = ["gemini", "qwen-vision", "gpt-4o"]
    
    def encode_image(self, image_bytes: bytes) -> str:
        """Convert image to base64 for API."""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def analyze(
        self,
        image_bytes: bytes,
        prompt: str = "Describe this image in detail.",
        model: str = "gemini"
    ) -> str:
        """Analyze image using vision-capable model."""
        b64_image = self.encode_image(image_bytes)
        
        # Construct multimodal message
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}"
                        }
                    }
                ]
            }
        ]
        
        # Use vision model if available, fallback to description
        try:
            response = self.client.chat(
                messages=messages,
                model=model,
                temperature=0.3
            )
            return response.get("content", "Vision analysis failed. Try describing the image instead.")
        except Exception as e:
            return f"Vision analysis failed: {str(e)}. Try describing the image instead."
    
    def extract_text(self, image_bytes: bytes) -> str:
        """OCR-like text extraction."""
        return self.analyze(
            image_bytes,
            "Extract all visible text from this image. Preserve formatting.",
            "gemini"
        )
