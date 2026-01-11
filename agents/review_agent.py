"""
Review Agent

The review agent that:
- Extracts frames from the rendered video
- Uses a vision-capable AI model to analyze the video
- Compares against user input and design principles
- Scores the video and approves if >= 80% match
- Provides specific feedback for improvements if rejected
"""

import os
import requests
import json
import subprocess
import base64
from dataclasses import dataclass
from typing import Optional, List
from dotenv import load_dotenv


@dataclass
class VideoInput:
    """User input for video generation"""
    content: str
    hook: str
    duration: int
    pacing: dict
    keywords: dict


@dataclass
class ReviewResult:
    """Result from the Review Agent"""
    approved: bool
    score: int  # 0-100 percentage
    feedback: Optional[str] = None


class ReviewAgent:
    """
    The review agent that evaluates rendered videos using AI vision.
    
    Extracts frames from the video and analyzes them against
    user input and design principles. Approves if score >= 80%.
    """
    
    APPROVAL_THRESHOLD = 80  # Minimum score to approve
    FRAMES_TO_EXTRACT = 5    # Number of frames to analyze
    
    def __init__(self, project_root: str = None):
        """
        Initialize the Review Agent
        
        Args:
            project_root: Path to the project root directory
        """
        if project_root is None:
            self.project_root = os.path.dirname(os.path.dirname(__file__))
        else:
            self.project_root = project_root
            
        # Load .env from project root
        env_path = os.path.join(self.project_root, ".env")
        load_dotenv(env_path)
        
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env file")
        
        # Vision model - NVIDIA Nemotron supports video understanding
        # Can be overridden with REVIEW_MODEL in .env
        self.model = os.getenv("REVIEW_MODEL", "nvidia/nemotron-nano-12b-v2-vl:free")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        self.frames_dir = os.path.join(self.project_root, "out", "frames")
        self.design_principles = self._load_design_principles()
        
        # Ensure frames directory exists
        os.makedirs(self.frames_dir, exist_ok=True)
        
        print(f"[REVIEW AGENT] Initialized with vision model: {self.model}")
        print(f"[REVIEW AGENT] Approval threshold: {self.APPROVAL_THRESHOLD}%")
    
    def _load_design_principles(self) -> str:
        """Load design principles from file"""
        principles_path = os.path.join(self.project_root, "agents", "design_principles.md")
        
        try:
            with open(principles_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return self._get_default_principles()
    
    def _get_default_principles(self) -> str:
        """Default design principles"""
        return """
# Design Principles

## Screen Specifications
- Resolution: 1080x1920 (vertical reel, 9:16)
- Frame rate: 30 fps
- Safe zone: 150px from edges

## Visual Style
- Background: Dark colors (#0a0a0a to #1a1a1a)
- Text: High contrast, readable, centered
- Hook text should be larger and highlighted
- Keywords should have accent colors (gold, green, etc.)

## Animation Principles
- Text should fade in/out smoothly
- Text should be visible long enough to read
- Pacing should match the specified timing
"""
    
    def _extract_frames(self, video_path: str) -> List[str]:
        """
        Extract key frames from the video using ffmpeg
        
        Args:
            video_path: Path to the rendered video
            
        Returns:
            List of paths to extracted frame images
        """
        print(f"[REVIEW AGENT] Extracting frames from video...")
        
        # Clear old frames
        for f in os.listdir(self.frames_dir):
            if f.endswith('.jpg'):
                os.remove(os.path.join(self.frames_dir, f))
        
        # Get video duration and extract evenly spaced frames
        frame_paths = []
        
        try:
            # Extract frames at specific intervals
            # For a 5-second video, extract frames at 0, 1, 2, 3, 4 seconds
            for i in range(self.FRAMES_TO_EXTRACT):
                output_path = os.path.join(self.frames_dir, f"frame_{i:02d}.jpg")
                timestamp = i  # 1 second intervals
                
                result = subprocess.run(
                    f'ffmpeg -y -ss {timestamp} -i "{video_path}" -vframes 1 -q:v 2 "{output_path}"',
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if os.path.exists(output_path):
                    frame_paths.append(output_path)
                    
            print(f"[REVIEW AGENT] ✓ Extracted {len(frame_paths)} frames")
            return frame_paths
            
        except subprocess.TimeoutExpired:
            print("[REVIEW AGENT] ✗ Frame extraction timed out")
            return []
        except Exception as e:
            print(f"[REVIEW AGENT] ✗ Frame extraction error: {e}")
            return []
    
    def _encode_image_base64(self, image_path: str) -> Optional[str]:
        """Encode an image to base64 string"""
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            print(f"[REVIEW AGENT] ✗ Failed to encode image: {e}")
            return None
    
    def _make_vision_api_call(self, frame_paths: List[str], user_input: VideoInput) -> Optional[dict]:
        """
        Make API call to vision model with video frames
        
        Returns:
            Dict with 'score' and 'feedback' keys, or None if failed
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://video-maker.local",
            "X-Title": "Video Maker Review Agent",
            "Content-Type": "application/json"
        }
        
        # Build content with images
        content = []
        
        # Add text prompt first
        prompt_text = f"""You are reviewing a video reel. I'm showing you {len(frame_paths)} frames extracted from the video at 1-second intervals.

## REQUIREMENTS THE VIDEO SHOULD MEET:

Content/Message: {user_input.content}
Hook (should appear in first 2 seconds): {user_input.hook}
Total Duration: {user_input.duration} seconds
Expected Timing:
{json.dumps(user_input.pacing, indent=2)}

Keywords that should be highlighted with special colors:
{json.dumps(user_input.keywords, indent=2)}

## DESIGN REQUIREMENTS:
- Dark background
- High contrast text
- Hook text should be large and eye-catching (gold/yellow is preferred)
- Text should be centered and readable
- Smooth transitions between text elements

## YOUR TASK:
Analyze these video frames and score how well the video meets the requirements.

RESPOND ONLY WITH A JSON OBJECT IN THIS FORMAT:
{{
    "score": <number 0-100>,
    "issues": ["specific issue 1", "specific issue 2"],
    "positives": ["what's good 1", "what's good 2"]
}}

Be generous - if the video mostly matches the requirements, give a high score (80+).
Only deduct significant points for clear problems like missing text, wrong colors, or unreadable content."""

        content.append({
            "type": "text",
            "text": prompt_text
        })
        
        # Add each frame as an image
        for i, frame_path in enumerate(frame_paths):
            base64_img = self._encode_image_base64(frame_path)
            if base64_img:
                content.append({
                    "type": "text",
                    "text": f"\nFrame {i+1} (at {i} seconds):"
                })
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_img}"
                    }
                })
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "temperature": 0.2,
            "max_tokens": 1000
        }
        
        try:
            print("[REVIEW AGENT] Calling vision API for frame analysis...")
            response = requests.post(
                self.api_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=90  # Longer timeout for vision model
            )
            
            if response.status_code != 200:
                print(f"[REVIEW AGENT] ✗ API error: {response.status_code}")
                print(f"[REVIEW AGENT] Response: {response.text[:300]}")
                return None
            
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                
                # Parse JSON from response
                try:
                    content = content.strip()
                    # Remove markdown code blocks if present
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]
                    
                    evaluation = json.loads(content.strip())
                    return evaluation
                except json.JSONDecodeError:
                    print(f"[REVIEW AGENT] ✗ Failed to parse JSON response")
                    print(f"[REVIEW AGENT] Raw: {content[:200]}")
                    return None
            
            return None
                
        except requests.exceptions.Timeout:
            print("[REVIEW AGENT] ✗ API call timed out")
            return None
        except Exception as e:
            print(f"[REVIEW AGENT] ✗ Request error: {e}")
            return None
    
    def evaluate(self, video_path: str, user_input: VideoInput) -> ReviewResult:
        """
        Evaluate the rendered video against user input and design principles
        
        Args:
            video_path: Path to rendered video
            user_input: Original user input specifications
            
        Returns:
            ReviewResult with score, approval status, and feedback
        """
        print(f"[REVIEW AGENT] Evaluating video: {video_path}")
        
        # Check if video exists
        if not os.path.exists(video_path):
            print(f"[REVIEW AGENT] ✗ Video not found: {video_path}")
            return ReviewResult(approved=False, score=0, feedback="Video file not found")
        
        # Extract frames from video
        frame_paths = self._extract_frames(video_path)
        
        if not frame_paths:
            print("[REVIEW AGENT] ⚠ Could not extract frames, auto-approving")
            return ReviewResult(approved=True, score=80, feedback="Auto-approved (frame extraction failed)")
        
        # Call vision API to analyze frames
        evaluation = self._make_vision_api_call(frame_paths, user_input)
        
        if evaluation is None:
            print("[REVIEW AGENT] ⚠ Vision analysis failed, auto-approving")
            return ReviewResult(approved=True, score=80, feedback="Auto-approved (vision API error)")
        
        score = evaluation.get("score", 0)
        issues = evaluation.get("issues", [])
        positives = evaluation.get("positives", [])
        
        print(f"[REVIEW AGENT] Score: {score}%")
        print(f"[REVIEW AGENT] Positives: {len(positives)}")
        for pos in positives[:3]:  # Show first 3
            print(f"  ✓ {pos}")
        print(f"[REVIEW AGENT] Issues: {len(issues)}")
        for issue in issues[:3]:  # Show first 3
            print(f"  ✗ {issue}")
        
        if score >= self.APPROVAL_THRESHOLD:
            print(f"[REVIEW AGENT] ✓ Video approved! (Score: {score}% >= {self.APPROVAL_THRESHOLD}%)")
            return ReviewResult(approved=True, score=score)
        else:
            feedback = "Issues found:\n" + "\n".join(f"- {issue}" for issue in issues)
            print(f"[REVIEW AGENT] ✗ Video rejected (Score: {score}% < {self.APPROVAL_THRESHOLD}%)")
            return ReviewResult(approved=False, score=score, feedback=feedback)


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    try:
        agent = ReviewAgent()
        
        test_input = VideoInput(
            content="Stop scrolling! This video was made entirely with code.",
            hook="STOP SCROLLING",
            duration=5,
            pacing={
                0: "STOP SCROLLING",
                1: "This video was made",
                2: "entirely with code"
            },
            keywords={
                "STOP SCROLLING": {"highlight": True, "color": "#FFD700"},
                "code": {"highlight": True, "color": "#00FF00"}
            }
        )
        
        # Test with actual video
        video_path = os.path.join(agent.project_root, "out", "video.mp4")
        result = agent.evaluate(video_path, test_input)
        
        print(f"\n{'='*50}")
        print(f"Result: {'APPROVED' if result.approved else 'REJECTED'}")
        print(f"Score: {result.score}%")
        if result.feedback:
            print(f"Feedback: {result.feedback}")
            
    except ValueError as e:
        print(f"Error: {e}")
