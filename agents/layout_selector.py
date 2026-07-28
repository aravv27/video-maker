"""
Layout Selector

Picks the optimal layout(s) for given content.
Uses a combination of:
- Content type analysis (text, code, quote, CTA)
- Tag matching
- Duration requirements
- Heuristic rules

Can be extended with ML-based selection later.
"""

import re
from typing import List, Optional, Dict, Any
from layout_schema import Layout
from layout_registry import LayoutRegistry


class LayoutSelector:
    """
    Selects optimal layouts based on content analysis.
    
    Selection Strategy:
    1. Analyze content to extract features (has_code, is_quote, is_cta, etc.)
    2. Map features to layout tags
    3. Score layouts by tag match
    4. Apply heuristic rules (duration fit, sequence compatibility)
    5. Return ranked layout IDs
    """
    
    def __init__(self, registry: LayoutRegistry = None):
        """
        Initialize the selector.
        
        Args:
            registry: LayoutRegistry to use. Creates new one if not provided.
        """
        self.registry = registry or LayoutRegistry()
        print(f"[LAYOUT SELECTOR] Initialized with {len(self.registry.get_all())} layouts")
    
    def _analyze_content(self, content: Dict[str, Any]) -> Dict[str, bool]:
        """
        Analyze content to extract features.
        
        Returns dict of feature flags like:
        - has_code: Contains code snippets
        - is_quote: Single quote/statement
        - is_cta: Call-to-action content
        - is_text_list: Multiple text lines
        - has_explanation: Contains explanatory content
        """
        features = {
            "has_code": False,
            "is_quote": False,
            "is_cta": False,
            "is_text_list": False,
            "has_explanation": False,
            "is_simple": False,
        }
        
        # Get text content for analysis
        text = content.get("content", "") or content.get("text", "") or ""
        pacing = content.get("pacing", {})
        
        # Check for code patterns
        code_indicators = ["function", "const ", "let ", "var ", "import ", "def ", "class ", "=>", "return "]
        if any(ind in text for ind in code_indicators):
            features["has_code"] = True
        
        # Check if it's a single quote (short, possibly with attribution)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) <= 2 and len(text) < 200:
            if content.get("attribution") or text.startswith('"') or text.startswith("'"):
                features["is_quote"] = True
        
        # Check for CTA patterns
        cta_patterns = ["follow", "subscribe", "like", "share", "comment", "tap", "click", "swipe", "dm me"]
        if any(pattern in text.lower() for pattern in cta_patterns):
            features["is_cta"] = True
        
        # Check if it's a text list (multiple pacing entries)
        if len(pacing) > 2:
            features["is_text_list"] = True
        
        # Check for explanation content
        if content.get("explanations"):
            features["has_explanation"] = True
        
        # Simple content (short, no special formatting)
        if len(text) < 100 and not features["has_code"]:
            features["is_simple"] = True
        
        return features
    
    def _features_to_tags(self, features: Dict[str, bool]) -> List[str]:
        """Convert content features to searchable tags"""
        tags = []
        
        if features["has_code"]:
            tags.extend(["code", "programming"])
        
        if features["is_quote"]:
            tags.extend(["quote", "centered", "minimal"])
        
        if features["is_cta"]:
            tags.extend(["cta", "ending", "call-to-action"])
        
        if features["is_text_list"]:
            tags.extend(["text-only", "stacking", "typewriter"])
        
        if features["has_explanation"]:
            tags.extend(["explanation", "walkthrough", "split"])
        
        if features["is_simple"]:
            tags.extend(["simple", "minimal"])
        
        # Default tag if nothing matches
        if not tags:
            tags = ["text-only", "simple"]
        
        return tags
    
    def select(self, content: Dict[str, Any], duration: int = None) -> str:
        """
        Select the best layout for given content.
        
        Args:
            content: Content dict with text, pacing, etc.
            duration: Target duration in seconds (optional)
        
        Returns:
            Layout ID of the best matching layout
        """
        # Analyze content
        features = self._analyze_content(content)
        print(f"[LAYOUT SELECTOR] Content features: {features}")
        
        # Convert to tags
        tags = self._features_to_tags(features)
        print(f"[LAYOUT SELECTOR] Searching for tags: {tags}")
        
        # Get matching layouts
        matches = self.registry.get_by_tags(tags)
        
        if not matches:
            print("[LAYOUT SELECTOR] No matches, using default L001")
            return "L001"
        
        # Apply duration filter if specified
        if duration and len(matches) > 1:
            matches = self._filter_by_duration(matches, duration)
        
        selected = matches[0]
        print(f"[LAYOUT SELECTOR] Selected: {selected.id} ({selected.name})")
        return selected.id
    
    def _filter_by_duration(self, layouts: List[Layout], duration: int) -> List[Layout]:
        """Filter layouts that work with the given duration"""
        suitable = []
        
        for layout in layouts:
            min_dur = layout.timing.get("min_duration", 0)
            if duration >= min_dur:
                suitable.append(layout)
        
        return suitable if suitable else layouts
    
    def select_sequence(self, scenes: List[Dict[str, Any]]) -> List[str]:
        """
        Select layouts for a multi-scene video.
        
        Args:
            scenes: List of scene dicts with content/duration
        
        Returns:
            List of layout IDs in order
        """
        sequence = []
        previous_id = None
        
        for i, scene in enumerate(scenes):
            content = scene.get("content", scene)
            duration = scene.get("duration")
            
            # Select best layout
            layout_id = self.select(content, duration)
            
            # Apply sequence rules
            layout_id = self._apply_sequence_rules(layout_id, previous_id, i, len(scenes))
            
            sequence.append(layout_id)
            previous_id = layout_id
        
        print(f"[LAYOUT SELECTOR] Selected sequence: {sequence}")
        return sequence
    
    def _apply_sequence_rules(
        self, 
        layout_id: str, 
        previous_id: Optional[str],
        index: int,
        total: int
    ) -> str:
        """
        Apply heuristic rules for layout sequences.
        
        Rules:
        - Don't repeat same layout consecutively (if alternatives exist)
        - Prefer CTA layouts for last scene
        - Prefer hook layouts for first scene
        """
        # If last scene, prefer CTA
        if index == total - 1:
            cta_layouts = self.registry.get_by_tags(["cta"])
            if cta_layouts:
                return cta_layouts[0].id
        
        # Avoid consecutive repeats
        if layout_id == previous_id:
            alternatives = self.registry.get_all()
            for alt in alternatives:
                if alt.id != layout_id:
                    return alt.id
        
        return layout_id
    
    def get_layout_for_content_type(self, content_type: str) -> str:
        """
        Quick lookup for common content types.
        
        Args:
            content_type: One of "hook", "code", "quote", "cta", "explain"
        
        Returns:
            Layout ID
        """
        type_to_layout = {
            "hook": "L001",
            "text": "L001",
            "code": "L002",
            "code_explain": "L003",
            "cta": "L004",
            "quote": "L005",
        }
        return type_to_layout.get(content_type, "L001")


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    selector = LayoutSelector()
    
    print("\n" + "="*50)
    print("LAYOUT SELECTOR TEST")
    print("="*50)
    
    # Test 1: Text content
    text_content = {
        "content": "Your skin deserves better. Stop hiding. Start glowing.",
        "pacing": {0: "Line 1", 2: "Line 2", 4: "Line 3"}
    }
    result = selector.select(text_content)
    print(f"\nText content → {result}")
    
    # Test 2: Code content
    code_content = {
        "content": "const x = 10;\nfunction hello() {\n  return 'world';\n}"
    }
    result = selector.select(code_content)
    print(f"Code content → {result}")
    
    # Test 3: Quote
    quote_content = {
        "content": "The only way to do great work is to love what you do.",
        "attribution": "— Steve Jobs"
    }
    result = selector.select(quote_content)
    print(f"Quote content → {result}")
    
    # Test 4: CTA
    cta_content = {
        "content": "Follow for more tips!"
    }
    result = selector.select(cta_content)
    print(f"CTA content → {result}")
    
    # Test 5: Multi-scene sequence
    scenes = [
        {"content": {"content": "Hook text here"}, "duration": 3},
        {"content": {"content": "const x = 10;"}, "duration": 5},
        {"content": {"content": "Follow me!"}, "duration": 3},
    ]
    sequence = selector.select_sequence(scenes)
    print(f"\nMulti-scene sequence: {sequence}")
