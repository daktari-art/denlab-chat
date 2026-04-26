"""Image generation feature for DenLab v4.0.
Enhanced with download support and aspect ratio parsing.
"""
import requests
import streamlit as st
from typing import Optional, Dict, Any
from core.api_client import PollinationsClient

class ImageGenerator:
    """Handle image generation with aspect ratio support and download."""
    
    def __init__(self):
        self.client = PollinationsClient()
        self.ratios = {
            "1:1": (1024, 1024),
            "16:9": (1024, 576),
            "9:16": (576, 1024),
            "4:3": (1024, 768),
            "3:4": (768, 1024),
            "21:9": (1024, 440),
        }
    
    def parse_command(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse /imagine command with optional --ar ratio.
        
        Args:
            text: Full command text (e.g., "/imagine a cat --ar 16:9")
            
        Returns:
            Dict with prompt, ratio, width, height or None if not an image command
        """
        if not text.lower().startswith('/imagine'):
            return None
        
        prompt = text[8:].strip()
        ratio = "1:1"
        
        # Parse --ar flag
        import re
        ar_match = re.search(r'--ar\s+(\d+:\d+)', prompt)
        if ar_match and ar_match.group(1) in self.ratios:
            ratio = ar_match.group(1)
            prompt = re.sub(r'--ar\s+\d+:\d+', '', prompt).strip()
        
        # Also support --model flag
        model = "flux"
        model_match = re.search(r'--model\s+(\w+)', prompt)
        if model_match:
            model = model_match.group(1)
            prompt = re.sub(r'--model\s+\w+', '', prompt).strip()
        
        # Also support --seed flag
        seed = None
        seed_match = re.search(r'--seed\s+(\d+)', prompt)
        if seed_match:
            seed = int(seed_match.group(1))
            prompt = re.sub(r'--seed\s+\d+', '', prompt).strip()
        
        w, h = self.ratios.get(ratio, (1024, 1024))
        
        return {
            "prompt": prompt,
            "ratio": ratio,
            "width": w,
            "height": h,
            "model": model,
            "seed": seed
        }
    
    def generate(self, prompt: str, ratio: str = "1:1", 
                 width: Optional[int] = None, height: Optional[int] = None,
                 model: str = "flux", seed: Optional[int] = None) -> str:
        """Generate image and return URL.
        
        Args:
            prompt: Image description
            ratio: Aspect ratio string (e.g., "16:9")
            width: Override width
            height: Override height
            model: Image model to use
            seed: Optional seed
            
        Returns:
            URL string for generated image
        """
        w, h = self.ratios.get(ratio, (1024, 1024))
        if width:
            w = width
        if height:
            h = height
            
        return self.client.generate_image(prompt, w, h, model, seed)
    
    def generate_with_download(self, prompt: str, ratio: str = "1:1",
                                width: Optional[int] = None, 
                                height: Optional[int] = None,
                                model: str = "flux",
                                seed: Optional[int] = None) -> Dict[str, Any]:
        """Generate image and attempt to download it.
        
        Args:
            prompt: Image description
            ratio: Aspect ratio
            width: Override width
            height: Override height
            model: Image model
            seed: Optional seed
            
        Returns:
            Dict with 'url', 'data' (bytes), and 'success'
        """
        url = self.generate(prompt, ratio, width, height, model, seed)
        img_data = self.client.download_image(url)
        
        return {
            "url": url,
            "data": img_data,
            "success": img_data is not None,
            "prompt": prompt,
            "ratio": ratio
        }
    
    def render_image_with_actions(self, img_url: str, msg_idx: int, 
                                   caption: str = ""):
        """Render image in Streamlit with download and copy actions.
        
        Args:
            img_url: URL of the image
            msg_idx: Message index for unique keys
            caption: Optional caption text
        """
        st.image(img_url, caption=caption or "Generated image", 
                use_container_width=True)
        
        cols = st.columns([1, 1, 1, 20])
        
        with cols[0]:
            # Try to download and provide download button
            try:
                img_data = requests.get(img_url, timeout=15).content
                st.download_button(
                    label="⬇️",
                    data=img_data,
                    file_name=f"denlab_image_{msg_idx}.png",
                    mime="image/png",
                    key=f"img_dl_{msg_idx}",
                    help="Download image"
                )
            except Exception:
                st.button("⬇️", key=f"img_dl_fail_{msg_idx}", 
                         help="Download unavailable", disabled=True)
        
        with cols[1]:
            # Copy URL button
            escaped_url = json.dumps(img_url)
            copy_js = f"""
            <script>
            function copy_img_url_{msg_idx}() {{
                navigator.clipboard.writeText({escaped_url}).then(function() {{
                    const btn = document.getElementById('copy_url_btn_{msg_idx}');
                    const orig = btn.innerHTML;
                    btn.innerHTML = '✓';
                    btn.style.color = '#3fb950';
                    setTimeout(() => {{ 
                        btn.innerHTML = orig; 
                        btn.style.color = ''; 
                    }}, 2000);
                }});
            }}
            </script>
            <button id="copy_url_btn_{msg_idx}" onclick="copy_img_url_{msg_idx}()" 
                style="background: transparent; border: none; color: #666; 
                       padding: 4px 8px; border-radius: 6px; cursor: pointer;
                       font-size: 14px;"
                onmouseover="this.style.background='#222'" 
                onmouseout="this.style.background='transparent'"
                title="Copy URL">
                🔗
            </button>
            """
            st.markdown(copy_js, unsafe_allow_html=True)
        
        with cols[2]:
            # Open in new tab
            open_js = f"""
            <script>
            function open_img_{msg_idx}() {{
                window.open({escaped_url}, '_blank');
            }}
            </script>
            <button onclick="open_img_{msg_idx}()" 
                style="background: transparent; border: none; color: #666; 
                       padding: 4px 8px; border-radius: 6px; cursor: pointer;
                       font-size: 14px;"
                onmouseover="this.style.background='#222'" 
                onmouseout="this.style.background='transparent'"
                title="Open in new tab">
                🖼️
            </button>
            """
            st.markdown(open_js, unsafe_allow_html=True)


# Convenience functions
def generate_image_url(prompt: str, width: int = 1024, height: int = 1024) -> str:
    """Quick image URL generation."""
    client = PollinationsClient()
    return client.generate_image(prompt, width, height)
