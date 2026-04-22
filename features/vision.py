"""Enhanced Vision capabilities - analyze uploaded images like Kimi."""
import base64
import io
import streamlit as st
from typing import Optional, List, Dict, Any
from PIL import Image

try:
    from core.api_client import get_client
except ImportError:
    get_client = None

class VisionAnalyzer:
    """Advanced image analysis with multiple capabilities."""
    
    def __init__(self):
        if get_client:
            self.client = get_client()
        else:
            self.client = None
        self.vision_models = ["gemini", "gpt-4o", "claude", "qwen"]
    
    def encode_image(self, image_bytes: bytes) -> str:
        """Convert image to base64 for API."""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def get_image_info(self, image_bytes: bytes) -> Dict[str, Any]:
        """Get basic image information (dimensions, format, size)."""
        try:
            img = Image.open(io.BytesIO(image_bytes))
            return {
                "width": img.width,
                "height": img.height,
                "format": img.format or "Unknown",
                "mode": img.mode,
                "size_bytes": len(image_bytes),
                "aspect_ratio": round(img.width / img.height, 2) if img.height > 0 else 0
            }
        except Exception as e:
            return {"error": str(e)}
    
    def analyze(
        self,
        image_bytes: bytes,
        prompt: str = "Describe this image in detail.",
        model: str = "gemini"
    ) -> str:
        """Analyze image using vision-capable model with enhanced prompts."""
        b64_image = self.encode_image(image_bytes)
        
        # Enhanced default prompt for comprehensive analysis
        if prompt == "Describe this image in detail.":
            prompt = """Analyze this image comprehensively. Include:
1. Overall scene/context description
2. All visible objects and their relationships
3. Any text visible in the image (transcribe it)
4. People - count, activities, expressions, clothing
5. Colors and visual style
6. Setting/location if identifiable
7. Any notable details or anomalies"""
        
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
        
        try:
            if self.client:
                response = self.client.chat(
                    messages=messages,
                    model=model,
                    temperature=0.3
                )
                result = response.get("content", "Vision analysis failed.")
            else:
                # Fallback using direct API
                import requests
                import json as json_mod
                
                api_url = "https://text.pollinations.ai/openai"
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.3
                }
                resp = requests.post(api_url, json=payload, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    result = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                else:
                    result = f"Vision API error: HTTP {resp.status_code}"
            
            # Add image metadata
            info = self.get_image_info(image_bytes)
            if "error" not in info:
                meta_text = f"\n\n---\n*Image: {info['width']}x{info['height']}px, {info['format']}, {self._format_size(info['size_bytes'])}*"
                result = result + meta_text
            
            return result
            
        except Exception as e:
            return f"Vision analysis failed: {str(e)}. Try describing the image in text instead."
    
    def extract_text(self, image_bytes: bytes) -> str:
        """OCR-like text extraction from images."""
        return self.analyze(
            image_bytes,
            "Extract ALL visible text from this image. Preserve the original formatting, line breaks, and structure as much as possible. Include text from signs, labels, screens, documents, or any other source.",
            "gemini"
        )
    
    def analyze_document(self, image_bytes: bytes) -> str:
        """Analyze document images (receipts, forms, papers)."""
        return self.analyze(
            image_bytes,
            "This is a document image. Analyze it as follows:\n1. Document type (receipt, form, letter, etc.)\n2. All text content (transcribe everything)\n3. Key information (dates, amounts, names, addresses)\n4. Layout description\n5. Any stamps, signatures, or special marks",
            "gemini"
        )
    
    def analyze_screenshot(self, image_bytes: bytes) -> str:
        """Analyze UI screenshots and interface images."""
        return self.analyze(
            image_bytes,
            "This is a screenshot of a user interface. Analyze:\n1. What application/website is shown\n2. All UI elements (buttons, menus, text fields, icons)\n3. Text content visible on screen\n4. Layout and design patterns\n5. User flow or current state\n6. Any error messages or notifications",
            "gemini"
        )
    
    def compare_images(self, image_bytes_list: List[bytes], prompt: str = "Compare these images.") -> str:
        """Compare multiple images."""
        if len(image_bytes_list) < 2:
            return "Need at least 2 images to compare."
        
        content = [{"type": "text", "text": prompt}]
        
        for img_bytes in image_bytes_list[:4]:  # Max 4 images
            b64 = self.encode_image(img_bytes)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
            })
        
        messages = [{"role": "user", "content": content}]
        
        try:
            if self.client:
                response = self.client.chat(messages=messages, model="gemini", temperature=0.3)
                return response.get("content", "Comparison failed.")
            else:
                import requests
                api_url = "https://text.pollinations.ai/openai"
                payload = {"model": "gemini", "messages": messages, "temperature": 0.3}
                resp = requests.post(api_url, json=payload, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return f"Comparison API error: HTTP {resp.status_code}"
        except Exception as e:
            return f"Image comparison failed: {str(e)}"
    
    def _format_size(self, size_bytes: int) -> str:
        """Format byte size to human readable."""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.1f}KB"
        else:
            return f"{size_bytes/(1024*1024):.1f}MB"


def analyze_uploaded_image(image_bytes: bytes, analysis_type: str = "general") -> str:
    """Convenience function for quick image analysis."""
    analyzer = VisionAnalyzer()
    
    analyzers = {
        "general": analyzer.analyze,
        "ocr": analyzer.extract_text,
        "document": analyzer.analyze_document,
        "screenshot": analyzer.analyze_screenshot,
    }
    
    func = analyzers.get(analysis_type, analyzer.analyze)
    return func(image_bytes)
