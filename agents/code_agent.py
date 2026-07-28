"""
Code Agent

The code generation agent that:
- Receives instructions from Supervisor Agent
- Uses OpenRouter API (Mistral Devstral model) to generate Remotion TSX code
- Writes the generated code to CodeReel.tsx
- Returns success/failure status

NEW: Layout-based generation
- Receives a layout template + content
- Fills placeholders in the template
- Much more constrained and deterministic
"""

import os
import re
import requests
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from layout_schema import Layout
from layout_registry import LayoutRegistry


class CodeAgent:
    """
    The code generation agent that uses LLM to generate Remotion code.
    
    Uses OpenRouter API with the Mistral Devstral model for code generation.
    """
    
    def __init__(self, project_root: str = None):
        """
        Initialize the Code Agent
        
        Args:
            project_root: Path to the project root directory
        """
        # Load environment variables from .env file
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
        
        self.model = "mistralai/devstral-2512:free"
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        self.code_reel_path = os.path.join(self.project_root, "src", "CodeReel.tsx")
        
        print(f"[CODE AGENT] Initialized with model: {self.model}")
    
    def _make_api_call(self, prompt: str) -> Optional[str]:
        """
        Make API call to OpenRouter
        
        Args:
            prompt: The instruction/prompt for code generation
            
        Returns:
            Generated code string or None if failed
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://video-maker.local",  # Optional
            "X-Title": "Video Maker Agent",  # Optional
            "Content-Type": "application/json"
        }
        
        system_prompt = """You are an expert Remotion developer. You generate clean, working TypeScript/TSX code for Remotion video compositions.

IMPORTANT RULES:
1. Output ONLY the code. No explanations, no markdown code blocks, no comments before or after.
2. Start directly with the import statement.
3. Export the component as `CodeReel`.
4. Only import what you use - no unused imports.
5. Use Remotion's AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig as needed.
6. Do NOT include background image - it's handled by the parent Composition component.
6. The video resolution is 1080x1920 (vertical reel format).
7. Make animations smooth and engaging.
8. Follow the timing/pacing exactly as specified in the instructions."""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Lower temperature for more consistent code
            "max_tokens": 4000
        }
        
        try:
            print("[CODE AGENT] Calling OpenRouter API...")
            response = requests.post(
                self.api_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"[CODE AGENT] ✗ API error: {response.status_code}")
                print(f"[CODE AGENT] Response: {response.text[:500]}")
                return None
            
            result = response.json()
            
            # Extract the generated content
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                print(f"[CODE AGENT] ✓ Received response ({len(content)} chars)")
                return content
            else:
                print(f"[CODE AGENT] ✗ Unexpected response format: {result}")
                return None
                
        except requests.exceptions.Timeout:
            print("[CODE AGENT] ✗ API call timed out")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[CODE AGENT] ✗ Request error: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"[CODE AGENT] ✗ JSON decode error: {e}")
            return None
    
    def _clean_code(self, raw_code: str) -> str:
        """
        Clean the generated code by removing markdown code blocks if present
        
        Args:
            raw_code: The raw generated code from the LLM
            
        Returns:
            Cleaned code ready to be written to file
        """
        code = raw_code.strip()
        
        # Remove markdown code blocks if present
        if code.startswith("```typescript") or code.startswith("```tsx"):
            code = code.split("\n", 1)[1]  # Remove first line
        elif code.startswith("```"):
            code = code[3:]  # Remove ```
            if code.startswith("\n"):
                code = code[1:]
        
        if code.endswith("```"):
            code = code[:-3].rstrip()
        
        return code
    
    def generate(self, instructions: str) -> bool:
        """
        Generate Remotion code based on instructions from Supervisor
        
        Args:
            instructions: Detailed instructions for code generation
            
        Returns:
            True if code was generated and written successfully, False otherwise
        """
        print("[CODE AGENT] Generating Remotion code...")
        
        # Make API call to generate code
        raw_code = self._make_api_call(instructions)
        
        if raw_code is None:
            print("[CODE AGENT] ✗ Failed to generate code")
            return False
        
        # Clean the code (remove markdown if present)
        code = self._clean_code(raw_code)
        
        # Validate the code starts with an import (basic sanity check)
        if not code.startswith("import"):
            print("[CODE AGENT] ✗ Generated code doesn't start with import statement")
            print(f"[CODE AGENT] First 100 chars: {code[:100]}")
            return False
        
        # Write to file
        try:
            with open(self.code_reel_path, 'w', encoding='utf-8') as f:
                f.write(code)
            print(f"[CODE AGENT] ✓ Code written to {self.code_reel_path}")
            return True
        except Exception as e:
            print(f"[CODE AGENT] ✗ Failed to write code: {e}")
            return False
    
    # ================================================================
    # LAYOUT-BASED GENERATION (NEW)
    # ================================================================
    
    def generate_from_layout(self, layout: Layout, content: Dict[str, Any]) -> bool:
        """
        Generate code by filling a layout template with content.
        
        This is the NEW deterministic generation method:
        1. Load the layout's TSX template
        2. Ask AI to fill the placeholders with provided content
        3. Write the result to CodeReel.tsx
        
        Args:
            layout: The Layout object with template info
            content: Dict mapping slot names to values
        
        Returns:
            True if successful, False otherwise
        """
        print(f"[CODE AGENT] Filling layout: {layout.id} ({layout.name})")
        
        # Load template
        registry = LayoutRegistry(os.path.join(self.project_root, "layouts"))
        template = registry.get_template_content(layout)
        
        if template is None:
            print(f"[CODE AGENT] ✗ Could not load template for {layout.id}")
            return False
        
        # Validate content against layout slots
        is_valid, errors = layout.validate_content(content)
        if not is_valid:
            print(f"[CODE AGENT] ⚠ Content validation warnings: {errors}")
        
        # Prepare slot-filling prompt
        prompt = self._prepare_layout_prompt(layout, template, content)
        
        # Generate filled code
        raw_code = self._make_api_call(prompt)
        
        if raw_code is None:
            print("[CODE AGENT] ✗ Failed to fill template")
            return False
        
        # Clean and write
        code = self._clean_code(raw_code)
        
        if not code.startswith("import"):
            print("[CODE AGENT] ✗ Filled code doesn't start with import")
            return False
        
        try:
            with open(self.code_reel_path, 'w', encoding='utf-8') as f:
                f.write(code)
            print(f"[CODE AGENT] ✓ Layout-based code written to {self.code_reel_path}")
            return True
        except Exception as e:
            print(f"[CODE AGENT] ✗ Failed to write code: {e}")
            return False
    
    def _prepare_layout_prompt(
        self, 
        layout: Layout, 
        template: str, 
        content: Dict[str, Any]
    ) -> str:
        """
        Prepare the prompt for layout slot-filling.
        
        The AI's job is constrained to:
        1. Replace placeholders with content values
        2. Keep the template structure intact
        3. Make minor adjustments if needed (like array formatting)
        """
        # Build content values section
        content_str = "CONTENT VALUES TO INSERT:\n"
        for slot in layout.slots:
            value = content.get(slot.name, slot.default)
            if value is not None:
                content_str += f"  {slot.name}: {json.dumps(value)}\n"
        
        # Build placeholder mapping
        placeholder_info = "PLACEHOLDERS TO REPLACE:\n"
        placeholder_info += "  {{LINES}} → the lines array\n"
        placeholder_info += "  {{CHARS_PER_SECOND}} → number value\n"
        placeholder_info += "  {{FONT_FAMILY}} → string value (in quotes)\n"
        placeholder_info += "  {{HOOK_FONT_SIZE}} → number value\n"
        placeholder_info += "  {{BODY_FONT_SIZE}} → number value\n"
        placeholder_info += "  And similar patterns for other slots\n"
        
        prompt = f"""TASK: Fill this Remotion template with the provided content values.

TEMPLATE (with placeholders like {{{{PLACEHOLDER}}}}):
```tsx
{template}
```

{content_str}

{placeholder_info}

RULES:
1. Replace ALL placeholders with the corresponding content values
2. Keep the template structure EXACTLY as is
3. For array values, format as valid TypeScript arrays
4. For string values, use proper quotes
5. For number values, use raw numbers (no quotes)
6. Output ONLY the complete filled code - no explanations
7. Start with the import statement

OUTPUT: Complete TypeScript/TSX code with all placeholders filled."""

        return prompt
    
    def generate_from_layout_simple(self, layout_id: str, content: Dict[str, Any]) -> bool:
        """
        Convenience method to generate from just a layout ID.
        
        Args:
            layout_id: The layout ID (e.g., "L001")
            content: Slot values
            
        Returns:
            True if successful
        """
        registry = LayoutRegistry(os.path.join(self.project_root, "layouts"))
        layout = registry.get_by_id(layout_id)
        
        if layout is None:
            print(f"[CODE AGENT] ✗ Layout not found: {layout_id}")
            return False
        
        return self.generate_from_layout(layout, content)
    
    # ================================================================
    # MULTI-SCENE SUPPORT
    # ================================================================
    
    def generate_scene(self, layout_id: str, content: Dict[str, Any], scene_index: int) -> Optional[str]:
        """
        Generate a single scene TSX file for multi-scene videos.
        
        Args:
            layout_id: The layout ID
            content: Content for this scene
            scene_index: Position in video (0, 1, 2, ...)
            
        Returns:
            Path to generated scene file, or None if failed
        """
        print(f"[CODE AGENT] Generating scene {scene_index} with layout {layout_id}")
        
        # Load layout
        registry = LayoutRegistry(os.path.join(self.project_root, "layouts"))
        layout = registry.get_by_id(layout_id)
        
        if layout is None:
            print(f"[CODE AGENT] ✗ Layout not found: {layout_id}")
            return None
        
        # Load template
        template = registry.get_template_content(layout)
        if template is None:
            print(f"[CODE AGENT] ✗ Template not found for {layout_id}")
            return None
        
        # Prepare slot-filling prompt
        prompt = self._prepare_scene_prompt(layout, template, content, scene_index)
        
        # Generate code
        raw_code = self._make_api_call(prompt)
        
        if raw_code is None:
            print(f"[CODE AGENT] ✗ Failed to generate scene {scene_index}")
            return None
        
        # Clean code
        code = self._clean_code(raw_code)
        
        if not code.startswith("import"):
            print(f"[CODE AGENT] ✗ Scene {scene_index} code doesn't start with import")
            return None
        
        # Write to scene file
        scene_dir = os.path.join(self.project_root, "src", "scenes")
        os.makedirs(scene_dir, exist_ok=True)
        
        scene_filename = f"Scene_{scene_index:03d}.tsx"
        scene_path = os.path.join(scene_dir, scene_filename)
        
        try:
            with open(scene_path, 'w', encoding='utf-8') as f:
                f.write(code)
            print(f"[CODE AGENT] ✓ Scene {scene_index} written to {scene_path}")
            return scene_path
        except Exception as e:
            print(f"[CODE AGENT] ✗ Failed to write scene: {e}")
            return None
    
    def _prepare_scene_prompt(
        self,
        layout: 'Layout',
        template: str,
        content: Dict[str, Any],
        scene_index: int
    ) -> str:
        """Prepare prompt for scene generation"""
        
        # Build content values section
        content_str = "CONTENT VALUES TO INSERT:\n"
        for slot in layout.slots:
            value = content.get(slot.name, slot.default)
            if value is not None:
                content_str += f"  {slot.name}: {json.dumps(value)}\n"
        
        # Add lines if present in content
        if "lines" in content:
            content_str += f"  lines: {json.dumps(content['lines'])}\n"
        
        # Scene-specific component name
        component_name = f"Scene_{scene_index:03d}"
        
        prompt = f"""TASK: Generate a Remotion scene component from this template.

SCENE: {component_name} (scene {scene_index} of the video)

TEMPLATE:
```tsx
{template}
```

{content_str}

RULES:
1. Replace ALL placeholders with content values
2. Change the component export name to "{component_name}"
3. Keep the template animation/styling logic
4. For array values, format as valid TypeScript arrays
5. Output ONLY the complete code - no explanations
6. Start with import statements

OUTPUT: Complete TypeScript/TSX scene component."""

        return prompt

# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    # Test the code agent
    try:
        agent = CodeAgent()
        
        test_instructions = """
        Generate Remotion code for a video reel with the following specifications:
        
        CONTENT: "Stop scrolling! This video was made entirely with code."
        
        HOOK (first 2 seconds): "STOP SCROLLING" - make it big and gold colored
        
        DURATION: 5 seconds (150 frames at 30fps)
        
        PACING:
        - 0s: "STOP SCROLLING"
        - 1.5s: "This video was made"
        - 3s: "entirely with code"
        
        DESIGN REQUIREMENTS:
        - Background: Dark (#0a0a0a)
        - Text: White with gold for hook
        - Use spring animations for text entry
        - Fade out before next text appears
        """
        
        success = agent.generate(test_instructions)
        print(f"\nTest result: {'Success' if success else 'Failed'}")
        
    except ValueError as e:
        print(f"Error: {e}")
        print("Make sure you have a .env file with OPENROUTER_API_KEY set")
