"""
Layout Schema

Defines the data structures for layouts:
- LayoutSlot: A placeholder in a layout that gets filled with content
- Layout: A complete layout definition with metadata and slots
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json


@dataclass
class LayoutSlot:
    """
    A slot in a layout that gets filled with content.
    
    Attributes:
        name: Unique identifier for this slot (e.g., "hookText", "lines")
        type: Data type ("text", "array", "color", "number", "code")
        required: Whether this slot must be provided
        description: Human-readable description of what this slot is for
        default: Default value if not provided
    """
    name: str
    type: str  # "text", "array", "color", "number", "code"
    required: bool = True
    description: str = ""
    default: Any = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "LayoutSlot":
        return cls(
            name=data["name"],
            type=data["type"],
            required=data.get("required", True),
            description=data.get("description", ""),
            default=data.get("default")
        )


@dataclass
class Layout:
    """
    A complete layout definition.
    
    Attributes:
        id: Unique identifier (e.g., "L001")
        name: Human-readable name
        description: When/how to use this layout
        slots: List of content slots to fill
        template_file: Path to the TSX template file
        tags: Tags for selection matching (e.g., ["hook", "text-only"])
        timing: Default timing configuration
        example_output: Optional example of filled template
    """
    id: str
    name: str
    description: str
    slots: List[LayoutSlot]
    template_file: str
    tags: List[str] = field(default_factory=list)
    timing: Dict[str, Any] = field(default_factory=dict)
    example_output: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Layout":
        """Create Layout from JSON dict"""
        slots = [LayoutSlot.from_dict(s) for s in data.get("slots", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            slots=slots,
            template_file=data["template_file"],
            tags=data.get("tags", []),
            timing=data.get("timing", {}),
            example_output=data.get("example_output")
        )
    
    @classmethod
    def from_json_file(cls, filepath: str) -> "Layout":
        """Load Layout from a JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def get_slot(self, name: str) -> Optional[LayoutSlot]:
        """Get a slot by name"""
        for slot in self.slots:
            if slot.name == name:
                return slot
        return None
    
    def get_required_slots(self) -> List[LayoutSlot]:
        """Get all required slots"""
        return [s for s in self.slots if s.required]
    
    def validate_content(self, content: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate that content matches slot requirements.
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check required slots are provided
        for slot in self.get_required_slots():
            if slot.name not in content:
                errors.append(f"Missing required slot: {slot.name}")
        
        # Check types (basic validation)
        for name, value in content.items():
            slot = self.get_slot(name)
            if slot is None:
                continue  # Allow extra content
            
            # Type checking
            if slot.type == "array" and not isinstance(value, list):
                errors.append(f"Slot '{name}' expects array, got {type(value).__name__}")
            elif slot.type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Slot '{name}' expects number, got {type(value).__name__}")
            elif slot.type == "text" and not isinstance(value, str):
                errors.append(f"Slot '{name}' expects text, got {type(value).__name__}")
        
        return len(errors) == 0, errors
    
    def __repr__(self) -> str:
        return f"Layout({self.id}: {self.name})"


@dataclass
class Scene:
    """
    A single scene in a multi-scene video.
    
    Attributes:
        layout_id: Which layout to use
        duration: Duration in seconds
        content: Slot values for this scene
        transition: Transition to next scene ("cut", "fade", "slide")
    """
    layout_id: str
    duration: float
    content: Dict[str, Any]
    transition: str = "cut"
    
    @classmethod
    def from_dict(cls, data: dict) -> "Scene":
        return cls(
            layout_id=data["layout_id"],
            duration=data["duration"],
            content=data["content"],
            transition=data.get("transition", "cut")
        )


@dataclass
class VideoScene:
    """
    A complete video composed of multiple scenes.
    
    Attributes:
        scenes: List of scenes in order
        total_duration: Total video duration (calculated or override)
    """
    scenes: List[Scene]
    total_duration: Optional[float] = None
    
    def __post_init__(self):
        if self.total_duration is None:
            self.total_duration = sum(s.duration for s in self.scenes)
    
    @classmethod
    def from_dict(cls, data: dict) -> "VideoScene":
        scenes = [Scene.from_dict(s) for s in data["scenes"]]
        return cls(
            scenes=scenes,
            total_duration=data.get("total_duration")
        )


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    # Test creating a layout programmatically
    test_layout = Layout(
        id="L001",
        name="Hook + Typewriter",
        description="Text stacks vertically, hook fades in, rest typewrite",
        slots=[
            LayoutSlot(name="lines", type="array", required=True, 
                      description="Array of line objects with text, start, color, isHook"),
            LayoutSlot(name="hookColor", type="color", required=False,
                      default="#FFB5C5", description="Color for the hook text"),
            LayoutSlot(name="charsPerSecond", type="number", required=False,
                      default=20, description="Typewriter speed")
        ],
        template_file="L001_template.tsx",
        tags=["text-only", "motivational", "simple", "stacking"],
        timing={"min_duration": 6, "seconds_per_line": 1.5}
    )
    
    print("Created layout:", test_layout)
    print("Required slots:", [s.name for s in test_layout.get_required_slots()])
    
    # Test validation
    valid_content = {
        "lines": [{"text": "Hello", "start": 0, "color": "#FFF", "isHook": True}],
        "hookColor": "#FFD700"
    }
    is_valid, errors = test_layout.validate_content(valid_content)
    print(f"Valid content: {is_valid}, errors: {errors}")
    
    invalid_content = {"hookColor": "#FFD700"}  # Missing required 'lines'
    is_valid, errors = test_layout.validate_content(invalid_content)
    print(f"Invalid content: {is_valid}, errors: {errors}")
