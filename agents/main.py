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
from typing import Optional, Dict, Any, List
import subprocess
import os

# Import real agents and database
from supervisor_agent import SupervisorAgent, VideoInput
from code_agent import CodeAgent
from tts_agent import TTSAgent
from database import VideoDatabase, generate_video_filename, generate_timestamp_id
from code_fixer import fix_code_reel_file

# Layout system imports
from layout_registry import LayoutRegistry
from layout_selector import LayoutSelector
from layout_schema import Layout
from layout_design_agent import LayoutDesignAgent
from scene_plan import ScenePlan, VideoDesign


# ============================================================
# WORKFLOW STATES
# ============================================================

class WorkflowState(Enum):
    # Two-agent architecture states
    DESIGN_VIDEO = "design_video"         # LayoutDesignAgent picks layouts
    GENERATE_SCENES = "generate_scenes"   # CodeAgent generates each scene
    # Original states
    SELECT_LAYOUT = "select_layout"       # Legacy: single layout selection
    GENERATE_CODE = "generate_code"
    FIX_CODE = "fix_code"
    VALIDATE_CODE = "validate_code"
    GENERATE_AUDIO = "generate_audio"
    RENDER_VIDEO = "render_video"
    SAVE_TO_DB = "save_to_db"
    COMPLETE = "complete"
    FAILED = "failed"


# ============================================================
# VIDEO RENDERER
# ============================================================

def render_video(output_filename: str = None) -> Optional[str]:
    """
    Run Remotion to render the video (without audio).
    Audio is merged separately via merge_audio_to_video().
    
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


def merge_audio_to_video(video_path: str, audio_dir: str, pacing: dict) -> Optional[str]:
    """
    Merge all audio segments into the video using ffmpeg.
    
    This is more reliable than Remotion's dynamic audio loading.
    Creates a combined audio track and merges it with the video.
    
    Args:
        video_path: Path to the rendered video (without audio)
        audio_dir: Path to the directory containing audio segments
        pacing: Pacing dict to know segment timings
        
    Returns:
        Path to the final video with audio, or original path if merge fails
    """
    import json
    
    project_root = os.path.dirname(os.path.dirname(__file__))
    
    # Check if ffmpeg is available
    try:
        subprocess.run("ffmpeg -version", capture_output=True, shell=True, check=True)
    except:
        print("[AUDIO MERGE] ⚠ ffmpeg not found, skipping audio merge")
        return video_path
    
    # Get video duration (approx from pacing)
    max_time = max(pacing.keys()) + 3  # last segment + 3 seconds buffer
    
    # Build ffmpeg filter for mixing audio at correct times
    audio_inputs = []
    filter_parts = []
    
    sorted_pacing = sorted(pacing.items())
    for i, (start_sec, _) in enumerate(sorted_pacing):
        audio_file = os.path.join(audio_dir, f"segment_{i}.mp3")
        if os.path.exists(audio_file):
            audio_inputs.append(f'-i "{audio_file}"')
            # adelay takes milliseconds
            delay_ms = int(start_sec * 1000)
            filter_parts.append(f"[{i+1}:a]adelay={delay_ms}|{delay_ms}[a{i}]")
    
    if not audio_inputs:
        print("[AUDIO MERGE] ⚠ No audio files found, skipping merge")
        return video_path
    
    # Create the mix filter
    mix_inputs = "".join([f"[a{i}]" for i in range(len(audio_inputs))])
    filter_complex = ";".join(filter_parts) + f";{mix_inputs}amix=inputs={len(audio_inputs)}:duration=longest[aout]"
    
    # Output path (replace .mp4 with _audio.mp4, then rename back)
    output_with_audio = video_path.replace(".mp4", "_with_audio.mp4")
    
    # Build ffmpeg command
    input_str = " ".join(audio_inputs)
    cmd = f'ffmpeg -y -i "{video_path}" {input_str} -filter_complex "{filter_complex}" -map 0:v -map "[aout]" -c:v copy -c:a aac -shortest "{output_with_audio}"'
    
    print("[AUDIO MERGE] Merging audio into video...")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60,
            shell=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode == 0 and os.path.exists(output_with_audio):
            # Replace original with version that has audio
            os.remove(video_path)
            os.rename(output_with_audio, video_path)
            print(f"[AUDIO MERGE] ✓ Audio merged successfully")
            return video_path
        else:
            print(f"[AUDIO MERGE] ⚠ ffmpeg failed: {result.stderr[:200]}")
            return video_path
            
    except Exception as e:
        print(f"[AUDIO MERGE] ⚠ Merge error: {e}")
        return video_path


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
# LAYOUT-BASED WORKFLOW (NEW)
# ============================================================

def run_layout_workflow(user_input: VideoInput, layout_id: str = None) -> str:
    """
    New layout-based workflow:
    1. Select layout (or use provided layout_id)
    2. Convert user input to layout content format
    3. Generate code by filling layout template
    4. Validate → Render → Save
    
    This is more deterministic than the freeform workflow.
    """
    print("\n" + "="*60)
    print("STARTING LAYOUT-BASED VIDEO WORKFLOW")
    print("="*60 + "\n")
    
    project_root = os.path.dirname(os.path.dirname(__file__))
    
    # Initialize components
    supervisor = SupervisorAgent()
    code_agent = CodeAgent()
    layout_selector = LayoutSelector()
    registry = LayoutRegistry()
    db = VideoDatabase()
    
    # State tracking
    state = WorkflowState.SELECT_LAYOUT
    code_attempts = 0
    last_feedback = None
    video_path = None
    generated_code = ""
    selected_layout = None
    layout_content = {}
    
    # Generate timestamp ID for this video (used for video filename and audio folder)
    timestamp_id = generate_timestamp_id()
    audio_dir = os.path.join(project_root, "public", "audio", timestamp_id)
    
    while True:
        print(f"\n[STATE] {state.value.upper()}")
        
        # -----------------------------
        # STATE: SELECT_LAYOUT
        # -----------------------------
        if state == WorkflowState.SELECT_LAYOUT:
            if layout_id:
                # Use explicitly provided layout
                selected_layout = registry.get_by_id(layout_id)
                if selected_layout:
                    print(f"[LAYOUT] Using specified layout: {layout_id}")
                else:
                    print(f"[LAYOUT] ⚠ Layout {layout_id} not found, auto-selecting...")
            
            if not selected_layout:
                # Auto-select based on content
                content_for_selection = {
                    "content": user_input.content,
                    "pacing": user_input.pacing,
                }
                selected_layout_id = layout_selector.select(content_for_selection, user_input.duration)
                selected_layout = registry.get_by_id(selected_layout_id)
            
            if selected_layout:
                print(f"[LAYOUT] ✓ Selected: {selected_layout.id} ({selected_layout.name})")
                # Convert user input to layout content format
                layout_content = convert_input_to_layout_content(user_input, selected_layout)
                state = WorkflowState.GENERATE_CODE
            else:
                print("[LAYOUT] ✗ No suitable layout found, falling back to freeform")
                return run_workflow(user_input)  # Fall back to old workflow
        
        # -----------------------------
        # STATE: GENERATE_CODE (layout-based)
        # -----------------------------
        elif state == WorkflowState.GENERATE_CODE:
            code_attempts += 1
            print(f"[ATTEMPT] Layout fill attempt {code_attempts}/{MAX_CODE_ATTEMPTS}")
            
            # Use layout-based generation
            success = code_agent.generate_from_layout(selected_layout, layout_content)
            
            if success:
                generated_code = read_generated_code(project_root)
                state = WorkflowState.FIX_CODE
            else:
                if code_attempts >= MAX_CODE_ATTEMPTS:
                    state = WorkflowState.FAILED
        
        # -----------------------------
        # STATE: FIX_CODE
        # -----------------------------
        elif state == WorkflowState.FIX_CODE:
            fix_code_reel_file(project_root)
            generated_code = read_generated_code(project_root)
            state = WorkflowState.VALIDATE_CODE
        
        # -----------------------------
        # STATE: VALIDATE_CODE
        # -----------------------------
        elif state == WorkflowState.VALIDATE_CODE:
            is_valid, error_msg = supervisor.validate_code()
            
            if is_valid:
                state = WorkflowState.GENERATE_AUDIO
            else:
                if code_attempts >= MAX_CODE_ATTEMPTS:
                    state = WorkflowState.FAILED
                else:
                    last_feedback = error_msg
                    state = WorkflowState.GENERATE_CODE
        
        # -----------------------------
        # STATE: GENERATE_AUDIO
        # -----------------------------
        elif state == WorkflowState.GENERATE_AUDIO:
            try:
                # Use timestamped audio directory to avoid overwriting
                tts_agent = TTSAgent(voice="en-US-AriaNeural", audio_dir=audio_dir)
                audio_segments = tts_agent.generate_all_segments(user_input.pacing)
                
                import json
                manifest_path = os.path.join(audio_dir, "manifest.json")
                with open(manifest_path, 'w') as f:
                    json.dump([{"start": s, "path": p} for s, p in audio_segments], f, indent=2)
                
                print(f"[AUDIO] ✓ Generated {len(audio_segments)} audio segments in {timestamp_id}/")
                state = WorkflowState.RENDER_VIDEO
            except Exception as e:
                print(f"[AUDIO] ✗ TTS failed: {e}")
                state = WorkflowState.RENDER_VIDEO
        
        # -----------------------------
        # STATE: RENDER_VIDEO
        # -----------------------------
        elif state == WorkflowState.RENDER_VIDEO:
            # Use the same timestamp_id for video filename
            video_filename = generate_video_filename(timestamp_id=timestamp_id)
            video_path = render_video(output_filename=video_filename)
            
            if video_path:
                # Merge audio using ffmpeg (more reliable than Remotion)
                video_path = merge_audio_to_video(video_path, audio_dir, user_input.pacing)
                state = WorkflowState.SAVE_TO_DB
            else:
                if code_attempts >= MAX_CODE_ATTEMPTS:
                    state = WorkflowState.FAILED
                else:
                    state = WorkflowState.GENERATE_CODE
        
        # -----------------------------
        # STATE: SAVE_TO_DB
        # -----------------------------
        elif state == WorkflowState.SAVE_TO_DB:
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
            print(f"[DATABASE] Used layout: {selected_layout.id}")
            state = WorkflowState.COMPLETE
        
        # -----------------------------
        # STATE: COMPLETE
        # -----------------------------
        elif state == WorkflowState.COMPLETE:
            print("\n" + "="*60)
            print("✓ LAYOUT WORKFLOW COMPLETE")
            print(f"Layout used: {selected_layout.id} ({selected_layout.name})")
            print(f"Video saved at: {video_path}")
            print("="*60 + "\n")
            return f"Success! Video at {video_path}"
        
        # -----------------------------
        # STATE: FAILED
        # -----------------------------
        elif state == WorkflowState.FAILED:
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
            print("✗ LAYOUT WORKFLOW FAILED")
            print("="*60 + "\n")
            return "Failed after maximum attempts"


def convert_input_to_layout_content(user_input: VideoInput, layout: Layout) -> Dict[str, Any]:
    """
    Convert VideoInput to layout content format based on layout slots.
    
    Different layouts expect different content structures.
    This function maps VideoInput fields to layout slots.
    """
    content = {}
    
    # L001: Hook + Typewriter
    if layout.id == "L001":
        lines = []
        for time_sec, text in sorted(user_input.pacing.items()):
            is_hook = (time_sec == 0 or text == user_input.hook)
            color = user_input.keywords.get(text, {}).get("color", "#2D3436")
            lines.append({
                "text": text,
                "start": float(time_sec),
                "color": color,
                "isHook": is_hook
            })
        content["lines"] = lines
        content["charsPerSecond"] = 20
        content["fontFamily"] = '"Playfair Display", Georgia, serif'
        content["hookFontSize"] = 72
        content["bodyFontSize"] = 56
    
    # L002: Code Reveal
    elif layout.id == "L002":
        content["code"] = user_input.content
        content["highlightLines"] = []
        content["title"] = user_input.hook or ""
        content["revealSpeed"] = 2
        content["theme"] = "dark"
    
    # L003: Split Explain
    elif layout.id == "L003":
        content["code"] = user_input.content
        content["explanations"] = []
        content["splitRatio"] = 0.5
    
    # L004: CTA Pulse
    elif layout.id == "L004":
        content["mainText"] = user_input.hook or user_input.content
        content["subText"] = ""
        content["emoji"] = "👇"
        content["mainColor"] = user_input.hook_color or "#FFD700"
        content["pulseIntensity"] = 1.1
    
    # L005: Quote Centered
    elif layout.id == "L005":
        content["quote"] = user_input.content
        content["attribution"] = ""
        content["quoteColor"] = "#FFFFFF"
        content["fontSize"] = 64
        content["showQuoteMarks"] = True
    
    else:
        # Generic fallback - include all data
        content["content"] = user_input.content
        content["hook"] = user_input.hook
        content["pacing"] = user_input.pacing
    
    return content


# ============================================================
# TWO-AGENT WORKFLOW (NEW)
# ============================================================

def run_two_agent_workflow(user_input: VideoInput) -> str:
    """
    New two-agent workflow:
    1. LayoutDesignAgent picks layout(s) (API call 1)
    2. CodeAgent generates scene(s) (API call 2+)
    3. Stitch scenes → Validate → Render → Save
    
    Uses multi_scene flag to determine single vs multi-scene mode.
    """
    mode = "MULTI-SCENE" if user_input.multi_scene else "SINGLE-SCENE"
    print("\n" + "="*60)
    print(f"STARTING TWO-AGENT VIDEO WORKFLOW ({mode})")
    print("="*60 + "\n")
    
    project_root = os.path.dirname(os.path.dirname(__file__))
    
    # Initialize agents
    design_agent = LayoutDesignAgent()
    code_agent = CodeAgent()
    supervisor = SupervisorAgent()
    db = VideoDatabase()
    
    # State tracking
    timestamp_id = generate_timestamp_id()
    audio_dir = os.path.join(project_root, "public", "audio", timestamp_id)
    video_path = None
    generated_code = ""
    video_design = None
    scene_files = []
    
    # =========================================
    # PHASE 1: Design (LayoutDesignAgent)
    # =========================================
    print("\n[PHASE 1] DESIGN VIDEO")
    print("-" * 40)
    
    video_design = design_agent.design(
        content=user_input.content,
        hook=user_input.hook,
        duration=user_input.duration,
        pacing=user_input.pacing,
        multi_scene=user_input.multi_scene
    )
    
    print(f"[DESIGN] ✓ {video_design}")
    
    # =========================================
    # PHASE 2: Generate Scenes (CodeAgent)
    # =========================================
    print("\n[PHASE 2] GENERATE SCENES")
    print("-" * 40)
    
    for scene in video_design.scenes:
        print(f"\n[SCENE {scene.scene_index}] Layout: {scene.layout_id}, Duration: {scene.duration}s")
        
        scene_path = code_agent.generate_scene(
            layout_id=scene.layout_id,
            content=scene.content,
            scene_index=scene.scene_index
        )
        
        if scene_path:
            scene_files.append({
                "path": scene_path,
                "duration": scene.duration,
                "index": scene.scene_index
            })
        else:
            print(f"[SCENE {scene.scene_index}] ✗ Generation failed")
    
    if not scene_files:
        print("[ERROR] No scenes generated, workflow failed")
        return "Failed: No scenes generated"
    
    print(f"\n[PHASE 2] ✓ Generated {len(scene_files)} scene(s)")
    
    # =========================================
    # PHASE 3: Generate Composition
    # =========================================
    print("\n[PHASE 3] GENERATE COMPOSITION")
    print("-" * 40)
    
    if len(scene_files) == 1:
        # Single scene - use as CodeReel.tsx but rename export
        code_reel_path = os.path.join(project_root, "src", "CodeReel.tsx")
        
        # Read scene file and rename export
        with open(scene_files[0]["path"], 'r', encoding='utf-8') as f:
            scene_code = f.read()
        
        # Rename Scene_000 to CodeReel for compatibility with Composition.tsx
        scene_code = scene_code.replace("export const Scene_000", "export const CodeReel")
        scene_code = scene_code.replace("Scene_000", "CodeReel")  # In case used elsewhere
        
        with open(code_reel_path, 'w', encoding='utf-8') as f:
            f.write(scene_code)
        
        print(f"[COMPOSITION] ✓ Single scene exported as CodeReel")
    else:
        # Multi-scene - generate Composition with scene imports
        generate_multi_scene_composition(project_root, scene_files, video_design)
        print(f"[COMPOSITION] ✓ Multi-scene composition generated")
    
    # =========================================
    # PHASE 4: Fix and Validate
    # =========================================
    print("\n[PHASE 4] FIX AND VALIDATE")
    print("-" * 40)
    
    fix_code_reel_file(project_root)
    is_valid, error_msg = supervisor.validate_code()
    
    if not is_valid:
        print(f"[VALIDATE] ✗ Validation failed: {error_msg[:200]}")
        return f"Failed: Validation error - {error_msg[:100]}"
    
    print("[VALIDATE] ✓ Code validation passed")
    
    # Read generated code for database
    code_reel_path = os.path.join(project_root, "src", "CodeReel.tsx")
    with open(code_reel_path, 'r', encoding='utf-8') as f:
        generated_code = f.read()
    
    # =========================================
    # PHASE 5: Generate Audio
    # =========================================
    print("\n[PHASE 5] GENERATE AUDIO")
    print("-" * 40)
    
    try:
        tts_agent = TTSAgent(voice="en-US-AriaNeural", audio_dir=audio_dir)
        audio_segments = tts_agent.generate_all_segments(user_input.pacing)
        print(f"[AUDIO] ✓ Generated {len(audio_segments)} segments in {timestamp_id}/")
    except Exception as e:
        print(f"[AUDIO] ⚠ TTS failed: {e}")
    
    # =========================================
    # PHASE 6: Render Video
    # =========================================
    print("\n[PHASE 6] RENDER VIDEO")
    print("-" * 40)
    
    video_filename = generate_video_filename(timestamp_id=timestamp_id)
    video_path = render_video(output_filename=video_filename)
    
    if not video_path:
        print("[RENDER] ✗ Video render failed")
        return "Failed: Video render error"
    
    # Merge audio
    video_path = merge_audio_to_video(video_path, audio_dir, user_input.pacing)
    print(f"[RENDER] ✓ Video rendered: {video_path}")
    
    # =========================================
    # PHASE 7: Save to Database
    # =========================================
    print("\n[PHASE 7] SAVE TO DATABASE")
    print("-" * 40)
    
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
    
    print(f"[DATABASE] ✓ Saved with ID: {video_id}")
    
    # =========================================
    # COMPLETE
    # =========================================
    print("\n" + "="*60)
    print("✓ TWO-AGENT WORKFLOW COMPLETE")
    print(f"  Mode: {mode}")
    print(f"  Scenes: {len(scene_files)}")
    print(f"  Layouts: {' → '.join(s.layout_id for s in video_design.scenes)}")
    print(f"  Video: {video_path}")
    print("="*60 + "\n")
    
    return f"Success! Video at {video_path}"


def generate_multi_scene_composition(project_root: str, scene_files: List[Dict], video_design: 'VideoDesign'):
    """
    Generate Composition.tsx that stitches multiple scenes.
    """
    fps = 30
    
    # Build imports
    imports = ["import { AbsoluteFill, Sequence } from 'remotion';"]
    for sf in scene_files:
        scene_name = f"Scene_{sf['index']:03d}"
        imports.append(f"import {{ {scene_name} }} from './scenes/{scene_name}';")
    
    # Build scene sequence
    sequences = []
    frame_offset = 0
    for sf in scene_files:
        scene_name = f"Scene_{sf['index']:03d}"
        duration_frames = sf['duration'] * fps
        sequences.append(f"""      <Sequence from={{{frame_offset}}} durationInFrames={{{duration_frames}}}>
        <{scene_name} />
      </Sequence>""")
        frame_offset += duration_frames
    
    # Build component
    composition_code = f"""{chr(10).join(imports)}

export const MyComposition = () => {{
  return (
    <AbsoluteFill>
{chr(10).join(sequences)}
    </AbsoluteFill>
  );
}};
"""
    
    comp_path = os.path.join(project_root, "src", "Composition.tsx")
    with open(comp_path, 'w', encoding='utf-8') as f:
        f.write(composition_code)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    # Simple cosmetics daily content - stacking text style
    test_input = VideoInput(
        content="""Your skin deserves better.
Stop hiding.
Start glowing.
3 ingredients.
Zero chemicals.
Try it today.""",
        
        hook="Your skin deserves better.",
        
        duration=12,  # 12 seconds total
        
        pacing={
            0: "Your skin deserves better.",
            2: "Stop hiding.",
            3.5: "Start glowing.",
            5: "3 ingredients.",
            6.5: "Zero chemicals.",
            8: "Try it today."
        },
        
        keywords={
            "Your skin deserves better.": {"color": "#FFB5C5"},
            "Stop hiding.": {"color": "#FFFFFF"},
            "Start glowing.": {"color": "#FFD700"},
            "3 ingredients.": {"color": "#FFFFFF"},
            "Zero chemicals.": {"color": "#4ECDC4"},
            "Try it today.": {"color": "#FF69B4"}
        },
        
        entry_animation="fadeIn",
        exit_animation=None,
        background_color=None,
        hook_color="#FFB5C5",
        
        # NEW: Multi-scene mode (set to True for multi-scene video)
        multi_scene=False
    )
    
    # Use the new two-agent workflow
    # - LayoutDesignAgent picks layout(s)
    # - CodeAgent generates scene(s)
    result = run_two_agent_workflow(test_input)
    print(f"Final result: {result}")



