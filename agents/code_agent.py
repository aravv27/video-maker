"""
Code Agent

The code generation agent that:
- Receives instructions from Supervisor Agent
- Uses OpenRouter API (Mistral Devstral model) to generate Remotion TSX code
- Writes the generated code to Composition.tsx
- Returns success/failure status
"""

import os
import requests
import json
from typing import Optional
from dotenv import load_dotenv


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
        
        self.composition_path = os.path.join(self.project_root, "src", "Composition.tsx")
        
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
3. Export the component as `MyComposition`.
4. Only import what you use - no unused imports.
5. Use Remotion's AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig as needed.
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
            with open(self.composition_path, 'w', encoding='utf-8') as f:
                f.write(code)
            print(f"[CODE AGENT] ✓ Code written to {self.composition_path}")
            return True
        except Exception as e:
            print(f"[CODE AGENT] ✗ Failed to write code: {e}")
            return False


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
