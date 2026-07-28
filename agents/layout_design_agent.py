"""
Layout Design Agent

Specialized agent that:
1. Analyzes user content
2. Picks appropriate layout(s)
3. Plans scene structure for multi-scene videos
4. Enforces hook constraint (first scene must be hook)

Separate from CodeAgent - one LLM call for design decisions only.
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from scene_plan import ScenePlan, VideoDesign, parse_video_design
from layout_registry import LayoutRegistry


class LayoutDesignAgent:
    """
    Agent that designs video structure by picking layouts.
    
    API Call 1 in the pipeline:
    - Receives user content
    - Returns VideoDesign with scene plans
    """
    
    def __init__(self):
        load_dotenv()
        
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")
        
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "mistralai/devstral-2512:free"
        
        # Load layout catalog for prompt
        project_root = os.path.dirname(os.path.dirname(__file__))
        self.registry = LayoutRegistry(os.path.join(project_root, "layouts"))
        
        print(f"[LAYOUT DESIGN] Initialized with {len(self.registry.get_all())} layouts")
    
    def design(
        self, 
        content: str, 
        hook: str,
        duration: int, 
        pacing: Dict[float, str],
        multi_scene: bool = False
    ) -> VideoDesign:
        """
        Design the video structure.
        
        Args:
            content: Full text content
            hook: Hook text (first attention grabber)
            duration: Total video duration in seconds
            pacing: Timing of text segments
            multi_scene: If True, pick multiple layouts
            
        Returns:
            VideoDesign with scene plans
        """
        print(f"[LAYOUT DESIGN] Designing video ({duration}s, multi_scene={multi_scene})")
        
        # Build the prompt
        prompt = self._build_prompt(content, hook, duration, pacing, multi_scene)
        
        # Call LLM
        response = self._call_llm(prompt)
        
        if response is None:
            # Fallback: single scene with L001
            print("[LAYOUT DESIGN] ⚠ LLM failed, using fallback")
            return self._fallback_design(content, duration, pacing)
        
        # Parse response
        try:
            design = self._parse_response(response, content, pacing)
            print(f"[LAYOUT DESIGN] ✓ Designed: {design}")
            return design
        except Exception as e:
            print(f"[LAYOUT DESIGN] ⚠ Parse error: {e}, using fallback")
            return self._fallback_design(content, duration, pacing)
    
    def _build_prompt(
        self, 
        content: str, 
        hook: str,
        duration: int, 
        pacing: Dict[float, str],
        multi_scene: bool
    ) -> str:
        """Build the layout design prompt"""
        
        # Build layout catalog description
        layouts_desc = "AVAILABLE LAYOUTS:\n"
        for layout in self.registry.get_all():
            tags_str = ", ".join(layout.tags)
            is_hook = "hook" in layout.tags
            layouts_desc += f"- {layout.id}: {layout.name}"
            if is_hook:
                layouts_desc += " [CAN BE HOOK]"
            layouts_desc += f"\n  Description: {layout.description}\n"
            layouts_desc += f"  Tags: {tags_str}\n"
            layouts_desc += f"  Duration range: {layout.timing.get('min_duration', 3)}-{layout.timing.get('max_duration', 15)}s\n"
        
        # Build pacing description
        pacing_str = "CONTENT PACING:\n"
        for time, text in sorted(pacing.items()):
            pacing_str += f"  {time}s: \"{text}\"\n"
        
        scene_count = "2-4 layouts" if multi_scene else "exactly 1 layout"
        
        prompt = f"""You are a video layout designer. Your job is to pick the best layout(s) for a short video.

{layouts_desc}

USER CONTENT:
{content}

HOOK (first thing viewers see): "{hook}"

DURATION: {duration} seconds

{pacing_str}

MULTI-SCENE MODE: {multi_scene}

RULES:
1. First scene MUST use a hook-capable layout (has [CAN BE HOOK] tag)
2. Pick {scene_count}
3. Assign appropriate duration to each scene (must sum to ~{duration}s)
4. For content field, specify which text segments go in that scene

OUTPUT FORMAT (JSON array):
[
  {{"layout_id": "L001", "duration": 6, "content": {{"text_segments": ["segment1", "segment2"]}}}}
]

Return ONLY the JSON array, no explanation."""

        return prompt
    
    def _call_llm(self, prompt: str) -> Optional[str]:
        """Call the LLM API"""
        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a video layout designer. Output only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,  # Lower temperature for more consistent output
                    "max_tokens": 1000
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                print(f"[LAYOUT DESIGN] ✗ API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"[LAYOUT DESIGN] ✗ Request error: {e}")
            return None
    
    def _parse_response(
        self, 
        response: str, 
        content: str, 
        pacing: Dict[float, str]
    ) -> VideoDesign:
        """Parse LLM response into VideoDesign"""
        
        # Clean response - extract JSON
        response = response.strip()
        if response.startswith("```"):
            # Remove markdown code blocks
            lines = response.split("\n")
            response = "\n".join(lines[1:-1])
        
        # Parse JSON
        data = json.loads(response)
        
        # Ensure it's a list
        if not isinstance(data, list):
            data = [data]
        
        # Create scene plans
        scenes = []
        for i, scene_data in enumerate(data):
            layout_id = scene_data.get("layout_id", "L001")
            
            # Validate layout exists
            if self.registry.get_by_id(layout_id) is None:
                layout_id = "L001"  # Fallback
            
            # Build content dict from pacing
            scene_content = self._build_scene_content(
                scene_data.get("content", {}),
                pacing,
                i,
                len(data)
            )
            
            scene = ScenePlan(
                layout_id=layout_id,
                duration=scene_data.get("duration", 5),
                content=scene_content,
                scene_index=i
            )
            scenes.append(scene)
        
        return VideoDesign(scenes=scenes)
    
    def _build_scene_content(
        self, 
        raw_content: Dict, 
        pacing: Dict[float, str],
        scene_index: int,
        total_scenes: int
    ) -> Dict[str, Any]:
        """Build content dict for a scene"""
        
        # Convert pacing to lines format
        sorted_pacing = sorted(pacing.items())
        
        if total_scenes == 1:
            # Single scene - all content
            lines = [
                {"text": text, "start": float(time), "isHook": i == 0}
                for i, (time, text) in enumerate(sorted_pacing)
            ]
        else:
            # Multi-scene - divide content
            items_per_scene = max(1, len(sorted_pacing) // total_scenes)
            start_idx = scene_index * items_per_scene
            end_idx = start_idx + items_per_scene if scene_index < total_scenes - 1 else len(sorted_pacing)
            
            scene_items = sorted_pacing[start_idx:end_idx]
            base_time = scene_items[0][0] if scene_items else 0
            
            lines = [
                {"text": text, "start": float(time) - base_time, "isHook": scene_index == 0 and i == 0}
                for i, (time, text) in enumerate(scene_items)
            ]
        
        return {
            "lines": lines,
            **raw_content
        }
    
    def _fallback_design(
        self, 
        content: str, 
        duration: int, 
        pacing: Dict[float, str]
    ) -> VideoDesign:
        """Fallback design when LLM fails"""
        
        # Build lines from pacing
        lines = [
            {"text": text, "start": float(time), "isHook": i == 0}
            for i, (time, text) in enumerate(sorted(pacing.items()))
        ]
        
        scene = ScenePlan(
            layout_id="L001",
            duration=duration,
            content={"lines": lines},
            scene_index=0
        )
        
        return VideoDesign(scenes=[scene])


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    agent = LayoutDesignAgent()
    
    test_content = """Your skin deserves better.
Stop hiding.
Start glowing.
3 ingredients.
Zero chemicals.
Try it today."""
    
    test_pacing = {
        0: "Your skin deserves better.",
        2: "Stop hiding.",
        3.5: "Start glowing.",
        5: "3 ingredients.",
        6.5: "Zero chemicals.",
        8: "Try it today."
    }
    
    # Test single-scene
    design = agent.design(
        content=test_content,
        hook="Your skin deserves better.",
        duration=12,
        pacing=test_pacing,
        multi_scene=False
    )
    print(f"\nSingle-scene result: {design}")
    
    # Test multi-scene
    design = agent.design(
        content=test_content,
        hook="Your skin deserves better.",
        duration=12,
        pacing=test_pacing,
        multi_scene=True
    )
    print(f"\nMulti-scene result: {design}")
    for scene in design.scenes:
        print(f"  {scene}")
