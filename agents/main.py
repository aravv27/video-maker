"""
Video Maker Workflow Orchestrator

Simplified pipeline:
1. Supervisor prepares instructions from user input
2. Code Agent generates Remotion code (max 3 attempts)
3. Supervisor validates code compiles
4. Video gets rendered with unique filename
5. Code + video saved to database
6. Done!

All generated code is stored in SQLite for reuse (video library).
"""

from enum import Enum
from typing import Optional
import subprocess
import os

# Import real agents and database
from supervisor_agent import SupervisorAgent, VideoInput
from code_agent import CodeAgent
from tts_agent import TTSAgent
from database import VideoDatabase, generate_video_filename
from code_fixer import fix_code_reel_file


# ============================================================
# WORKFLOW STATES
# ============================================================

class WorkflowState(Enum):
    GENERATE_CODE = "generate_code"
    FIX_CODE = "fix_code"  # Auto-fix common issues
    VALIDATE_CODE = "validate_code"
    GENERATE_AUDIO = "generate_audio"  # TTS audio generation
    RENDER_VIDEO = "render_video"
    SAVE_TO_DB = "save_to_db"
    COMPLETE = "complete"
    FAILED = "failed"


# ============================================================
# VIDEO RENDERER
# ============================================================

def render_video(output_filename: str = None) -> Optional[str]:
    """
    Run Remotion to render the video
    
    Args:
        output_filename: Optional custom filename, defaults to unique timestamp
        
    Returns:
        Path to the rendered video, or None if failed
    """
    print("[RENDERER] Starting video render...")
    
    project_root = os.path.dirname(os.path.dirname(__file__))
    
    # Use unique filename if not provided
    if output_filename is None:
        output_filename = generate_video_filename()
    
    # Ensure output directory exists
    out_dir = os.path.join(project_root, "out")
    os.makedirs(out_dir, exist_ok=True)
    
    output_path = os.path.join(out_dir, output_filename)
    
    try:
        result = subprocess.run(
            f'npx remotion render MyComp "{output_path}"',
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120,
            shell=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode == 0:
            print(f"[RENDERER] ✓ Video rendered to {output_path}")
            return output_path
        else:
            print(f"[RENDERER] ✗ Render failed: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("[RENDERER] ✗ Render timed out")
        return None
    except Exception as e:
        print(f"[RENDERER] ✗ Render error: {e}")
        return None


def read_generated_code(project_root: str) -> str:
    """Read the current CodeReel.tsx code"""
    code_reel_path = os.path.join(project_root, "src", "CodeReel.tsx")
    try:
        with open(code_reel_path, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return ""


# ============================================================
# MAIN WORKFLOW
# ============================================================

MAX_CODE_ATTEMPTS = 3


def run_workflow(user_input: VideoInput) -> str:
    """
    Main workflow: Generate → Validate → Render → Save to DB → Done
    
    All generated code is stored in SQLite for reuse.
    Videos are saved with unique timestamps.
    """
    print("\n" + "="*60)
    print("STARTING VIDEO GENERATION WORKFLOW")
    print("="*60 + "\n")
    
    project_root = os.path.dirname(os.path.dirname(__file__))
    
    # Initialize agents and database
    supervisor = SupervisorAgent()
    code_agent = CodeAgent()
    db = VideoDatabase()
    
    # State tracking
    state = WorkflowState.GENERATE_CODE
    code_attempts = 0
    last_feedback = None
    video_path = None
    generated_code = ""
    
    while True:
        print(f"\n[STATE] {state.value.upper()}")
        
        # -----------------------------
        # STATE: GENERATE_CODE
        # -----------------------------
        if state == WorkflowState.GENERATE_CODE:
            code_attempts += 1
            print(f"[ATTEMPT] Code generation attempt {code_attempts}/{MAX_CODE_ATTEMPTS}")
            
            # Supervisor prepares instructions
            instructions = supervisor.prepare_instructions(user_input, last_feedback)
            
            # Code Agent generates code
            success = code_agent.generate(instructions)
            
            if success:
                generated_code = read_generated_code(project_root)
                state = WorkflowState.FIX_CODE  # Go to auto-fix first
            else:
                if code_attempts >= MAX_CODE_ATTEMPTS:
                    state = WorkflowState.FAILED
                # else stay in GENERATE_CODE to retry
        
        # -----------------------------
        # STATE: FIX_CODE (Auto-fix TypeScript issues)
        # -----------------------------
        elif state == WorkflowState.FIX_CODE:
            fix_code_reel_file(project_root)
            generated_code = read_generated_code(project_root)  # Re-read after fix
            state = WorkflowState.VALIDATE_CODE
        
        # -----------------------------
        # STATE: VALIDATE_CODE
        # -----------------------------
        elif state == WorkflowState.VALIDATE_CODE:
            is_valid, error_msg = supervisor.validate_code()
            
            if is_valid:
                state = WorkflowState.GENERATE_AUDIO  # Go to TTS generation
            else:
                if code_attempts >= MAX_CODE_ATTEMPTS:
                    state = WorkflowState.FAILED
                else:
                    last_feedback = supervisor.incorporate_feedback("", error_msg)
                    state = WorkflowState.GENERATE_CODE
        
        # -----------------------------
        # STATE: GENERATE_AUDIO (TTS)
        # -----------------------------
        elif state == WorkflowState.GENERATE_AUDIO:
            try:
                tts_agent = TTSAgent(voice="en-US-AriaNeural")  # Female voice
                tts_agent.clear_audio_files()  # Remove old audio
                
                # Generate audio for each segment
                audio_segments = tts_agent.generate_all_segments(user_input.pacing)
                
                # Save audio manifest for Composition to use
                import json
                manifest_path = os.path.join(project_root, "public", "audio", "manifest.json")
                with open(manifest_path, 'w') as f:
                    json.dump([{"start": s, "path": p} for s, p in audio_segments], f, indent=2)
                
                print(f"[AUDIO] ✓ Generated {len(audio_segments)} audio segments")
                state = WorkflowState.RENDER_VIDEO
            except Exception as e:
                print(f"[AUDIO] ✗ TTS generation failed: {e}")
                # Continue without audio
                state = WorkflowState.RENDER_VIDEO
        
        # -----------------------------
        # STATE: RENDER_VIDEO
        # -----------------------------
        elif state == WorkflowState.RENDER_VIDEO:
            video_path = render_video()  # Uses unique filename
            
            if video_path:
                state = WorkflowState.SAVE_TO_DB
            else:
                # Render failed - treat as code issue
                if code_attempts >= MAX_CODE_ATTEMPTS:
                    state = WorkflowState.FAILED
                else:
                    last_feedback = "Video render failed. Check the code for runtime errors."
                    state = WorkflowState.GENERATE_CODE
        
        # -----------------------------
        # STATE: SAVE_TO_DB
        # -----------------------------
        elif state == WorkflowState.SAVE_TO_DB:
            # Save to database for code reuse / video library
            video_id = db.save_video(
                input_content=user_input.content,
                input_hook=user_input.hook,
                input_duration=user_input.duration,
                input_pacing=user_input.pacing,
                input_keywords=user_input.keywords,
                generated_code=generated_code,
                video_path=video_path,
                status="success"
            )
            print(f"[DATABASE] Video saved with ID: {video_id}")
            state = WorkflowState.COMPLETE
        
        # -----------------------------
        # STATE: COMPLETE
        # -----------------------------
        elif state == WorkflowState.COMPLETE:
            print("\n" + "="*60)
            print("✓ WORKFLOW COMPLETE")
            print(f"Video saved at: {video_path}")
            print("="*60 + "\n")
            return f"Success! Video at {video_path}"
        
        # -----------------------------
        # STATE: FAILED
        # -----------------------------
        elif state == WorkflowState.FAILED:
            # Still save to DB but mark as failed
            if generated_code:
                db.save_video(
                    input_content=user_input.content,
                    input_hook=user_input.hook,
                    input_duration=user_input.duration,
                    input_pacing=user_input.pacing,
                    input_keywords=user_input.keywords,
                    generated_code=generated_code,
                    video_path=None,
                    status="failed"
                )
            
            print("\n" + "="*60)
            print("✗ WORKFLOW FAILED")
            print("Max attempts reached without producing valid code")
            print("="*60 + "\n")
            return "Failed after maximum attempts"


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    # Simple cosmetics daily content - stacking text style
    # Each line appears and STAYS on screen
    test_input = VideoInput(
        content="""Your skin deserves better.
Stop hiding.
Start glowing.
3 ingredients.
Zero chemicals.
Try it today.""",
        
        hook="Your skin deserves better.",
        
        duration=12,  # 12 seconds total
        
        # Lines appear at these times (and STAY visible)
        pacing={
            0: "Your skin deserves better.",
            2: "Stop hiding.",
            3.5: "Start glowing.",
            5: "3 ingredients.",
            6.5: "Zero chemicals.",
            8: "Try it today."
        },
        
        # Simple color assignments
        keywords={
            "Your skin deserves better.": {"color": "#FFB5C5"},
            "Stop hiding.": {"color": "#FFFFFF"},
            "Start glowing.": {"color": "#FFD700"},
            "3 ingredients.": {"color": "#FFFFFF"},
            "Zero chemicals.": {"color": "#4ECDC4"},
            "Try it today.": {"color": "#FF69B4"}
        },
        
        entry_animation="fadeIn",
        exit_animation=None,  # No exit - lines stay!
        background_color=None,
        hook_color="#FFB5C5"
    )
    
    result = run_workflow(test_input)
    print(f"Final result: {result}")

