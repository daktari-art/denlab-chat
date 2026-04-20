"""Text-to-speech and audio features."""
import streamlit as st
from core.api_client import get_client

class AudioGenerator:
    def __init__(self):
        self.client = get_client()
        self.voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    
    def speak(self, text: str, voice: str = "nova") -> str:
        """Generate audio URL for text."""
        if len(text) > 4000:
            text = text[:4000] + "..."
        return self.client.generate_audio(text, voice)
    
    def render_player(self, audio_url: str):
        """Render audio player in Streamlit."""
        st.audio(audio_url, format='audio/mp3')
    
    def narrate_message(self, message: str, auto_play: bool = False):
        """Add narration to a message."""
        audio_url = self.speak(message)
        if auto_play:
            st.markdown(f'<audio src="{audio_url}" autoplay controls style="width:100%"></audio>', 
                       unsafe_allow_html=True)
        else:
            st.audio(audio_url)
