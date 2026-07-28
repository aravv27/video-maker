"""
Scene Plan Dataclass

Represents a planned scene in a multi-scene video.
Created by LayoutDesignAgent, consumed by CodeAgent.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ScenePlan:
    """
    A single scene in a video.
    
    Created by LayoutDesignAgent during the "design" phase.
    Consumed by CodeAgent during the "generate" phase.
    """
    layout_id: str              # e.g., "L001"
    duration: int               # Duration in seconds
    content: Dict[str, Any]     # Content to fill into layout slots
    scene_index: int = 0        # Position in video (0 = first scene)
    
    def __repr__(self):
        return f"ScenePlan(layout={self.layout_id}, duration={self.duration}s, index={self.scene_index})"


@dataclass
class VideoDesign:
    """
    Complete video design - output of LayoutDesignAgent.
    
    Contains all scenes planned for a video.
    """
    scenes: List[ScenePlan]
    total_duration: int = 0
    
    def __post_init__(self):
        """Calculate total duration from scenes"""
        self.total_duration = sum(s.duration for s in self.scenes)
    
    @property
    def scene_count(self) -> int:
        return len(self.scenes)
    
    @property
    def is_multi_scene(self) -> bool:
        return len(self.scenes) > 1
    
    def __repr__(self):
        layouts = " → ".join(s.layout_id for s in self.scenes)
        return f"VideoDesign({self.scene_count} scenes: {layouts}, total={self.total_duration}s)"


# Helper to create from JSON (from LLM output)
def parse_video_design(data: List[Dict]) -> VideoDesign:
    """
    Parse LLM JSON output into VideoDesign.
    
    Expected format:
    [
        {"layout_id": "L001", "duration": 6, "content": {...}},
        {"layout_id": "L004", "duration": 3, "content": {...}},
    ]
    """
    scenes = []
    for i, scene_data in enumerate(data):
        scene = ScenePlan(
            layout_id=scene_data.get("layout_id", "L001"),
            duration=scene_data.get("duration", 5),
            content=scene_data.get("content", {}),
            scene_index=i
        )
        scenes.append(scene)
    
    return VideoDesign(scenes=scenes)
