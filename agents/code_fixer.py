"""
Code Fixer

Automatically fixes common TypeScript issues in generated Remotion code:
1. Removes unused imports (spring, useVideoConfig, etc.)
2. Removes unused variable declarations (fps, etc.)
3. Adds types to function parameters

This runs AFTER the AI generates code and BEFORE validation.
"""

import re
import os


def fix_unused_imports(code: str) -> str:
    """Remove unused imports from the Remotion import statement"""
    
    # Find the remotion import line
    import_match = re.search(
        r"import\s*\{([^}]+)\}\s*from\s*['\"]remotion['\"];?",
        code
    )
    
    if not import_match:
        return code
    
    original_import = import_match.group(0)
    imports_str = import_match.group(1)
    
    # Parse individual imports
    imports = [i.strip() for i in imports_str.split(',')]
    
    # Check which imports are actually used in the code (excluding the import line itself)
    code_without_import = code.replace(original_import, '')
    
    used_imports = []
    for imp in imports:
        # Check if the import is used elsewhere in the code
        # Use word boundary to avoid partial matches
        if re.search(rf'\b{re.escape(imp)}\b', code_without_import):
            used_imports.append(imp)
    
    if not used_imports:
        # Keep at least AbsoluteFill if nothing else
        used_imports = ['AbsoluteFill']
    
    # Rebuild the import statement
    new_import = f"import {{ {', '.join(used_imports)} }} from 'remotion';"
    
    fixed_code = code.replace(original_import, new_import)
    
    if original_import != new_import:
        removed = set(imports) - set(used_imports)
        if removed:
            print(f"[CODE FIXER] Removed unused imports: {', '.join(removed)}")
    
    return fixed_code


def fix_unused_variables(code: str) -> str:
    """Remove unused variable declarations like 'const { fps } = useVideoConfig()'"""
    
    # Pattern: const { fps } = useVideoConfig();
    # Only remove if fps is not used elsewhere
    
    patterns = [
        # const { fps } = useVideoConfig();
        (r"const\s*\{\s*fps\s*\}\s*=\s*useVideoConfig\(\);?\s*\n?", 'fps'),
        # const { fps, ... } = useVideoConfig() - just remove fps
        (r"const\s*\{\s*fps\s*,\s*", 'fps'),
        (r",\s*fps\s*\}", 'fps'),
    ]
    
    fixed_code = code
    
    for pattern, var_name in patterns:
        match = re.search(pattern, fixed_code)
        if match:
            # Check if variable is used elsewhere (excluding the declaration)
            code_without_decl = fixed_code.replace(match.group(0), '')
            if not re.search(rf'\b{var_name}\b', code_without_decl):
                # Variable not used, remove the declaration
                if pattern == patterns[0][0]:
                    # Remove entire line
                    fixed_code = re.sub(pattern, '', fixed_code)
                    print(f"[CODE FIXER] Removed unused variable: {var_name}")
                # For partial patterns, we'd need more complex logic
    
    return fixed_code


def fix_function_types(code: str) -> str:
    """Add types to function parameters that have implicit 'any'"""
    
    # Common patterns that need types
    fixes = [
        # getEffectStyle = (effect, frame) => ...
        (
            r'const\s+getEffectStyle\s*=\s*\(\s*effect\s*,\s*frame\s*\)',
            'const getEffectStyle = (effect: string | undefined, frame: number)'
        ),
        # Similar patterns for other common functions
        (
            r'const\s+getOpacity\s*=\s*\(\s*start\s*,\s*end\s*\)',
            'const getOpacity = (start: number, end: number)'
        ),
        (
            r'const\s+getEntryAnimation\s*=\s*\(\s*type\s*,\s*start\s*\)',
            'const getEntryAnimation = (type: string, start: number)'
        ),
    ]
    
    fixed_code = code
    
    for pattern, replacement in fixes:
        if re.search(pattern, fixed_code):
            fixed_code = re.sub(pattern, replacement, fixed_code)
            print(f"[CODE FIXER] Added types to function parameters")
    
    return fixed_code


def fix_remotion_code(code: str) -> str:
    """
    Apply all fixes to the generated Remotion code.
    
    Args:
        code: The raw generated TypeScript/TSX code
        
    Returns:
        Fixed code that should pass TypeScript validation
    """
    print("[CODE FIXER] Analyzing generated code...")
    
    # Apply fixes in order
    fixed = code
    fixed = fix_unused_imports(fixed)
    fixed = fix_unused_variables(fixed)
    fixed = fix_function_types(fixed)
    
    if fixed != code:
        print("[CODE FIXER] ✓ Applied fixes to generated code")
    else:
        print("[CODE FIXER] No fixes needed")
    
    return fixed


def fix_code_reel_file(project_root: str) -> bool:
    """
    Fix the CodeReel.tsx file in place.
    
    Args:
        project_root: Path to the project root
        
    Returns:
        True if fixes were applied, False otherwise
    """
    code_reel_path = os.path.join(project_root, "src", "CodeReel.tsx")
    
    try:
        with open(code_reel_path, 'r', encoding='utf-8') as f:
            original_code = f.read()
        
        fixed_code = fix_remotion_code(original_code)
        
        if fixed_code != original_code:
            with open(code_reel_path, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
            return True
        
        return False
        
    except Exception as e:
        print(f"[CODE FIXER] Error: {e}")
        return False


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    # Test with sample code
    test_code = """import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';

export const MyComposition = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const getEffectStyle = (effect, frame) => {
    switch (effect) {
      case 'glow':
        return { textShadow: '0 0 20px rgba(255, 182, 193, 0.8)' };
      default:
        return {};
    }
  };

  return (
    <AbsoluteFill style={{ backgroundColor: '#0a0a0a' }}>
      <div style={{ opacity: interpolate(frame, [0, 30], [0, 1]) }}>
        Hello World
      </div>
    </AbsoluteFill>
  );
};
"""
    
    print("Original code:")
    print("-" * 50)
    print(test_code[:200] + "...")
    print()
    
    fixed = fix_remotion_code(test_code)
    
    print("\nFixed code:")
    print("-" * 50)
    print(fixed[:300] + "...")
