"""
Supervisor Agent

The orchestrator agent that:
- Processes user input (VideoInput)
- Loads and applies design principles
- Prepares detailed instructions for the Code Agent
- Validates generated code compiles
- Incorporates review feedback for iterations
"""

import subprocess
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class VideoInput:
    """User input for video generation"""
    content: str              # Main text content for the reel
    hook: str                 # First 2 seconds - what to highlight
    duration: int             # Duration in seconds
    pacing: dict              # Timestamps for text timing
    keywords: dict            # Words to highlight/zoom {word: {color, effect}}
    # Optional animation settings (fallback to design principles if not provided)
    entry_animation: Optional[str] = None    # spring, fadeIn, scaleUp, slideUp
    exit_animation: Optional[str] = None     # fadeOut, scaleDown
    background_color: Optional[str] = None   # e.g., '#0a0a0a'
    hook_color: Optional[str] = None         # e.g., '#FFD700'


class SupervisorAgent:
    """
    The orchestrator agent that manages the video generation workflow.
    
    Responsibilities:
    1. Load design principles from file
    2. Prepare comprehensive instructions for Code Agent
    3. Validate that generated code compiles
    4. Incorporate feedback from Review Agent
    """
    
    def __init__(self, project_root: str = None):
        """
        Initialize the Supervisor Agent
        
        Args:
            project_root: Path to the project root directory
        """
        if project_root is None:
            # Default to parent of agents folder
            self.project_root = os.path.dirname(os.path.dirname(__file__))
        else:
            self.project_root = project_root
            
        self.design_principles = self._load_design_principles()
        print(f"[SUPERVISOR] Initialized with project root: {self.project_root}")
    
    def _load_design_principles(self) -> str:
        """
        Load design principles from the design_principles.md file
        
        Returns:
            String containing all design principles
        """
        principles_path = os.path.join(self.project_root, "agents", "design_principles.md")
        
        try:
            with open(principles_path, 'r', encoding='utf-8') as f:
                principles = f.read()
                print(f"[SUPERVISOR] ✓ Loaded design principles from {principles_path}")
                return principles
        except FileNotFoundError:
            print(f"[SUPERVISOR] ⚠ Design principles file not found at {principles_path}")
            print("[SUPERVISOR] Using default principles...")
            return self._get_default_principles()
    
    def _get_default_principles(self) -> str:
        """
        Default design principles if file is not found
        """
        return """
# Design Principles for Video Generation

## Screen Specifications
- Resolution: 1080x1920 (vertical reel format, 9:16 aspect ratio)
- Frame rate: 30 fps
- Safe zone: Keep text 150px from edges to avoid UI overlap

## Visual Style
- Background: Dark colors (#0a0a0a to #1a1a1a)
- Text: High contrast, readable fonts (min 48px for body, 72px+ for hooks)
- Colors: Use vibrant accent colors for keywords (#FFD700 gold, #00FF00 green, #FF6B6B coral)

## Animation Principles
- Loop: First and last frames should visually connect for seamless looping
- Entry: Use spring animations for text appearing (scale from 0.8 to 1.0)
- Exit: Fade out before next element (opacity 1 to 0 over 10-15 frames)
- Pacing: Each text element should be readable (minimum 1 second per short phrase)

## Value Drop Techniques
- Word highlighting: Emphasize keywords with different colors
- Word jitters: Subtle scale or position animation on key words
- Progressive reveal: Show text word-by-word or line-by-line

## Code Requirements
- Use Remotion's AbsoluteFill as the root container
- Use useCurrentFrame() and useVideoConfig() hooks
- Use interpolate() for smooth value transitions
- Use spring() for natural-feeling animations
- Export component as MyComposition
"""
    
    def prepare_instructions(self, user_input: VideoInput, feedback: Optional[str] = None) -> str:
        """
        Prepare detailed instructions for the Code Agent
        
        Combines:
        - User input (content, hook, duration, pacing, keywords)
        - Design principles
        - Any feedback from previous review
        
        Args:
            user_input: The VideoInput containing all user specifications
            feedback: Optional feedback from Review Agent to address
            
        Returns:
            Comprehensive instruction string for Code Agent
        """
        # Build the pacing section
        pacing_text = ""
        if user_input.pacing:
            pacing_text = "TIMING/PACING (second: text to show):\n"
            for second, text in sorted(user_input.pacing.items()):
                pacing_text += f"  - {second}s: \"{text}\"\n"
        
        # Build the keywords section
        keywords_text = ""
        if user_input.keywords:
            keywords_text = "KEYWORDS TO HIGHLIGHT:\n"
            for word, style in user_input.keywords.items():
                keywords_text += f"  - \"{word}\": {style}\n"
        
        # Compose full instructions
        instructions = f"""
================================================================================
TASK: Generate Remotion TSX code for a video reel
================================================================================

CONTENT REQUIREMENTS:
---------------------
Main Message: {user_input.content}

Hook (first 2 seconds): {user_input.hook}

Total Duration: {user_input.duration} seconds ({user_input.duration * 30} frames at 30fps)

{pacing_text}
{keywords_text}
"""
        
        # Add animation/style settings if specified by user
        style_text = ""
        if user_input.entry_animation:
            style_text += f"Entry Animation: {user_input.entry_animation}\n"
        if user_input.exit_animation:
            style_text += f"Exit Animation: {user_input.exit_animation}\n"
        if user_input.background_color:
            style_text += f"Background Color: {user_input.background_color}\n"
        if user_input.hook_color:
            style_text += f"Hook Color: {user_input.hook_color}\n"
        
        if style_text:
            instructions += f"""
STYLE/ANIMATION (USE THESE, not defaults):
-------------------------------------------
{style_text}
"""
        
        instructions += f"""================================================================================
DESIGN PRINCIPLES (FOLLOW STRICTLY):
================================================================================
{self.design_principles}

================================================================================
CODE REQUIREMENTS:
================================================================================
1. Generate a complete, working Remotion component
2. Export the component as `CodeReel`
3. Import from 'remotion': AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig
4. Only import what you use (no unused imports)
5. The component must render correctly at 1080x1920 resolution
6. Make the animation smooth and engaging
7. Follow the pacing/timing exactly as specified
8. Do NOT include any background image - the parent Composition handles that

OUTPUT FORMAT:
--------------
Return ONLY the TypeScript/TSX code. No explanations, no markdown code blocks.
Start directly with the import statement.
"""
        
        # Add feedback section if there's previous feedback to address
        if feedback:
            instructions += f"""
================================================================================
⚠️ PREVIOUS FEEDBACK TO ADDRESS:
================================================================================
{feedback}

Please fix the issues mentioned above while maintaining all other requirements.
"""
        
        print(f"[SUPERVISOR] Prepared instructions ({len(instructions)} chars)")
        return instructions
    
    def validate_code(self) -> tuple[bool, str]:
        """
        Validate that the generated code compiles without errors
        
        Returns:
            Tuple of (success: bool, error_message: str)
        """
        print("[SUPERVISOR] Validating code...")
        
        try:
            result = subprocess.run(
                "npx tsc --noEmit",
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
                shell=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode == 0:
                print("[SUPERVISOR] ✓ Code validation passed")
                return True, ""
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                print(f"[SUPERVISOR] ✗ Code validation failed:")
                print(error_msg[:500])
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            print("[SUPERVISOR] ✗ Code validation timed out")
            return False, "TypeScript compilation timed out after 30 seconds"
        except Exception as e:
            print(f"[SUPERVISOR] ✗ Code validation error: {e}")
            return False, str(e)
    
    def incorporate_feedback(self, review_feedback: str, compile_error: str = None) -> str:
        """
        Combine review feedback and any compile errors into actionable feedback
        
        Args:
            review_feedback: Feedback from the Review Agent
            compile_error: Any compilation errors from validation
            
        Returns:
            Combined feedback string for next iteration
        """
        combined = []
        
        if compile_error:
            combined.append(f"COMPILATION ERRORS:\n{compile_error}")
        
        if review_feedback:
            combined.append(f"REVIEW FEEDBACK:\n{review_feedback}")
        
        return "\n\n".join(combined)


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    # Test the supervisor agent
    supervisor = SupervisorAgent()
    
    test_input = VideoInput(
        content="Stop scrolling! This video was made entirely with code. No editing software needed.",
        hook="STOP SCROLLING",
        duration=5,
        pacing={
            0: "STOP SCROLLING",
            1: "This video was made",
            2: "entirely with code",
            3: "No editing software",
            4: "needed."
        },
        keywords={
            "STOP SCROLLING": {"highlight": True, "color": "#FFD700"},
            "code": {"highlight": True, "color": "#00FF00"}
        }
    )
    
    # Test instruction generation
    instructions = supervisor.prepare_instructions(test_input)
    print("\n" + "="*60)
    print("GENERATED INSTRUCTIONS:")
    print("="*60)
    print(instructions)
    
    # Test with feedback
    instructions_with_feedback = supervisor.prepare_instructions(
        test_input, 
        feedback="The text appears too fast. Slow down the transitions."
    )
    print("\n" + "="*60)
    print("INSTRUCTIONS WITH FEEDBACK:")
    print("="*60)
    print(instructions_with_feedback[-500:])  # Last 500 chars
