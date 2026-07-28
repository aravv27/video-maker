"""
Layout Registry

Loads, validates, and manages the layout catalog.
Provides methods to:
- Load all layouts from the layouts/ directory
- Get layouts by ID or tags
- Validate layout definitions
"""

import os
import json
from typing import List, Optional, Dict
from layout_schema import Layout, LayoutSlot


class LayoutRegistry:
    """
    Central registry for all available layouts.
    
    Loads layouts from JSON files in the layouts/ directory
    and provides lookup methods for the selector.
    """
    
    def __init__(self, layouts_dir: str = None):
        """
        Initialize the registry.
        
        Args:
            layouts_dir: Path to layouts directory. 
                        Defaults to project_root/layouts/
        """
        if layouts_dir is None:
            project_root = os.path.dirname(os.path.dirname(__file__))
            self.layouts_dir = os.path.join(project_root, "layouts")
        else:
            self.layouts_dir = layouts_dir
        
        self.templates_dir = os.path.join(self.layouts_dir, "templates")
        self._layouts: Dict[str, Layout] = {}
        self._load_all()
    
    def _load_all(self) -> None:
        """Load all layout JSON files from the layouts directory"""
        if not os.path.exists(self.layouts_dir):
            print(f"[LAYOUT REGISTRY] ⚠ Layouts directory not found: {self.layouts_dir}")
            return
        
        loaded = 0
        for filename in os.listdir(self.layouts_dir):
            if filename.endswith('.json') and filename != 'registry.json':
                filepath = os.path.join(self.layouts_dir, filename)
                try:
                    layout = Layout.from_json_file(filepath)
                    self._layouts[layout.id] = layout
                    loaded += 1
                except Exception as e:
                    print(f"[LAYOUT REGISTRY] ⚠ Failed to load {filename}: {e}")
        
        print(f"[LAYOUT REGISTRY] ✓ Loaded {loaded} layouts")
    
    def get_all(self) -> List[Layout]:
        """Get all registered layouts"""
        return list(self._layouts.values())
    
    def get_by_id(self, layout_id: str) -> Optional[Layout]:
        """Get a specific layout by ID"""
        return self._layouts.get(layout_id)
    
    def get_by_tags(self, tags: List[str], match_all: bool = False) -> List[Layout]:
        """
        Get layouts matching given tags.
        
        Args:
            tags: List of tags to match
            match_all: If True, layout must have ALL tags. 
                      If False, layout must have ANY tag.
        
        Returns:
            List of matching layouts, sorted by match score
        """
        results = []
        
        for layout in self._layouts.values():
            layout_tags = set(layout.tags)
            query_tags = set(tags)
            
            if match_all:
                if query_tags.issubset(layout_tags):
                    results.append((layout, len(query_tags)))
            else:
                matches = len(query_tags.intersection(layout_tags))
                if matches > 0:
                    results.append((layout, matches))
        
        # Sort by match score (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results]
    
    def get_template_path(self, layout: Layout) -> str:
        """Get the full path to a layout's template file"""
        return os.path.join(self.templates_dir, layout.template_file)
    
    def get_template_content(self, layout: Layout) -> Optional[str]:
        """Load the TSX template content for a layout"""
        template_path = self.get_template_path(layout)
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"[LAYOUT REGISTRY] ⚠ Template not found: {template_path}")
            return None
    
    def validate_layout(self, layout: Layout) -> tuple[bool, List[str]]:
        """
        Validate a layout definition.
        
        Checks:
        - Required fields are present
        - Template file exists
        - Slots are well-defined
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check required fields
        if not layout.id:
            errors.append("Missing layout ID")
        if not layout.name:
            errors.append("Missing layout name")
        if not layout.template_file:
            errors.append("Missing template file")
        
        # Check template exists
        template_path = self.get_template_path(layout)
        if not os.path.exists(template_path):
            errors.append(f"Template file not found: {layout.template_file}")
        
        # Check slots
        if not layout.slots:
            errors.append("Layout has no slots defined")
        else:
            slot_names = set()
            for slot in layout.slots:
                if slot.name in slot_names:
                    errors.append(f"Duplicate slot name: {slot.name}")
                slot_names.add(slot.name)
                
                valid_types = ["text", "array", "color", "number", "code"]
                if slot.type not in valid_types:
                    errors.append(f"Invalid slot type '{slot.type}' for slot '{slot.name}'")
        
        return len(errors) == 0, errors
    
    def list_layouts(self) -> str:
        """Get a formatted string listing all layouts (for AI context)"""
        lines = ["Available Layouts:", ""]
        
        for layout in self._layouts.values():
            lines.append(f"ID: {layout.id}")
            lines.append(f"  Name: {layout.name}")
            lines.append(f"  Description: {layout.description}")
            lines.append(f"  Tags: {', '.join(layout.tags)}")
            lines.append(f"  Slots: {', '.join(s.name for s in layout.slots)}")
            lines.append("")
        
        return "\n".join(lines)
    
    def reload(self) -> None:
        """Reload all layouts from disk"""
        self._layouts.clear()
        self._load_all()


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    registry = LayoutRegistry()
    
    print("\n" + "="*50)
    print("LAYOUT REGISTRY TEST")
    print("="*50)
    
    all_layouts = registry.get_all()
    print(f"\nTotal layouts: {len(all_layouts)}")
    
    for layout in all_layouts:
        print(f"\n{layout}")
        is_valid, errors = registry.validate_layout(layout)
        print(f"  Valid: {is_valid}")
        if errors:
            print(f"  Errors: {errors}")
    
    print("\n" + registry.list_layouts())
