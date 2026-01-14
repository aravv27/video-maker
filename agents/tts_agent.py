"""
TTS Agent using Edge TTS

Generates text-to-speech audio for each text segment using Microsoft Edge TTS.
- Free, no API key required
- Works on CPU
- High quality neural voices
"""

import edge_tts
import asyncio
import os
from typing import List, Tuple


class TTSAgent:
    """
    Text-to-Speech agent using Microsoft Edge TTS.
    
    Generates separate audio files for each text segment to sync with video.
    """
    
    def __init__(self, voice: str = "en-US-AriaNeural"):
        """
        Initialize TTS Agent.
        
        Args:
            voice: Voice ID to use. Options:
                - en-US-AriaNeural (female, natural)
                - en-US-JennyNeural (female, warm)
                - en-US-GuyNeural (male, natural)
                - en-IN-NeerjaNeural (female, Indian English)
        """
        self.voice = voice
        self.project_root = os.path.dirname(os.path.dirname(__file__))
        self.audio_dir = os.path.join(self.project_root, "public", "audio")
        
        # Ensure audio directory exists
        os.makedirs(self.audio_dir, exist_ok=True)
        
        print(f"[TTS AGENT] Initialized with voice: {self.voice}")
    
    async def _generate_single(self, text: str, output_path: str):
        """Generate a single audio file."""
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_path)
    
    def generate_segment(self, text: str, segment_index: int) -> str:
        """
        Generate audio for a single segment.
        
        Args:
            text: Text to convert to speech
            segment_index: Index of the segment (for filename)
            
        Returns:
            Path to the generated audio file (relative to public/)
        """
        filename = f"segment_{segment_index}.mp3"
        output_path = os.path.join(self.audio_dir, filename)
        
        print(f"[TTS AGENT] Generating audio for segment {segment_index}: '{text[:50]}...'")
        
        asyncio.run(self._generate_single(text, output_path))
        
        print(f"[TTS AGENT] ✓ Saved to {output_path}")
        
        # Return path relative to public/ for Remotion
        return f"audio/{filename}"
    
    def generate_all_segments(self, pacing: dict) -> List[Tuple[float, str]]:
        """
        Generate audio for all segments based on pacing.
        
        Args:
            pacing: Dictionary of {start_second: text} from VideoInput
            
        Returns:
            List of (start_second, relative_audio_path) tuples
        """
        print(f"[TTS AGENT] Generating audio for {len(pacing)} segments...")
        
        audio_segments = []
        
        for i, (start_second, text) in enumerate(sorted(pacing.items())):
            audio_path = self.generate_segment(text, i)
            audio_segments.append((start_second, audio_path))
        
        print(f"[TTS AGENT] ✓ Generated {len(audio_segments)} audio files")
        
        return audio_segments
    
    def clear_audio_files(self):
        """Remove all previously generated audio files."""
        for f in os.listdir(self.audio_dir):
            if f.endswith('.mp3'):
                os.remove(os.path.join(self.audio_dir, f))
        print("[TTS AGENT] Cleared previous audio files")


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    agent = TTSAgent()
    
    # Test with sample pacing
    test_pacing = {
        0: "Your skin deserves better.",
        2.5: "Stop hiding. Start glowing.",
        5: "3 ingredients. Zero chemicals.",
    }
    
    audio_segments = agent.generate_all_segments(test_pacing)
    
    print("\nGenerated audio segments:")
    for start, path in audio_segments:
        print(f"  {start}s: {path}")
