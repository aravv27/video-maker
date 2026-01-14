"""
Simple Render Script with TTS

Just generates audio and renders video - no AI code generation.
Edit the lines in CodeReel.tsx directly before running.
"""

import subprocess
import os
from datetime import datetime
from tts_agent import TTSAgent


def render_with_audio():
    """Generate TTS audio and render video"""
    
    project_root = os.path.dirname(os.path.dirname(__file__))
    
    # Lines to speak (should match CodeReel.tsx)
    pacing = {
        0: "Your skin deserves better.",
        2: "Stop hiding.",
        3.5: "Start glowing.",
        5: "3 ingredients.",
        6.5: "Zero chemicals.",
        8: "Try it today."
    }
    
    print("=" * 50)
    print("RENDERING VIDEO WITH TTS")
    print("=" * 50)
    
    # Step 1: Generate TTS audio
    print("\n[1/2] Generating TTS audio...")
    try:
        tts = TTSAgent(voice="en-US-AriaNeural")
        tts.clear_audio_files()
        tts.generate_all_segments(pacing)
        print("✓ Audio generated")
    except Exception as e:
        print(f"✗ TTS failed: {e}")
        print("Continuing without audio...")
    
    # Step 2: Render video
    print("\n[2/2] Rendering video...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(project_root, "out", f"video_{timestamp}.mp4")
    
    render_cmd = [
        "npx", "remotion", "render",
        "MyComp",
        output_path
    ]
    
    result = subprocess.run(render_cmd, cwd=project_root, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ Video saved to: {output_path}")
        return output_path
    else:
        print(f"✗ Render failed: {result.stderr}")
        return None


if __name__ == "__main__":
    render_with_audio()
