# Design Principles for Remotion Video Generation

> These are **fallback rules**. If the user specifies animation/style in their input, USE THEIR SPECIFICATION. 
> Only use these defaults when user doesn't specify.

---

## ⚠️ TYPESCRIPT RULES (MUST FOLLOW - CODE WILL NOT COMPILE OTHERWISE)

### 1. ONLY import what you use
```tsx
// ❌ WRONG - spring is imported but never used
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';

// ✅ CORRECT - only import what's actually used in the code
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
```

### 2. ONLY declare variables you use
```tsx
// ❌ WRONG - fps is declared but never used
const { fps } = useVideoConfig();

// ✅ CORRECT - don't destructure unused variables
// Just don't include useVideoConfig() if you don't need fps
```

### 3. ALWAYS add types to function parameters
```tsx
// ❌ WRONG - implicit 'any' type
const getEffectStyle = (effect, frame) => { ... }

// ✅ CORRECT - explicit types
const getEffectStyle = (effect: string | undefined, frame: number) => { ... }
```

### 4. Parts array must have typed interface
```tsx
// Define part type if using effects
interface Part {
  text: string;
  color: string;
  effect?: string;
}

// Then use it
const parts: Part[] = [
  { text: "Hello ", color: '#FFFFFF' },
  { text: "world", color: '#FF0000', effect: 'glow' }
];
```

---

## 1. Screen Specifications

| Property | Value |
|----------|-------|
| Resolution | 1080x1920 (vertical reel, 9:16) |
| Frame Rate | 30 fps |
| Safe Zone | 150px from all edges |

---

## 2. Safe Zone Layout

Text must stay away from:
- **Bottom 200px**: Instagram/TikTok caption area
- **Top 100px**: Status bar, time, notifications
- **Sides 80px**: Edge clarity

```tsx
padding: '100px 80px 200px 80px'  // top, right, bottom, left
```

---

## 3. Loop Continuity

The reel should **visually connect first and last frames**:
- Same background color throughout
- No jarring transitions at loop point
- Consider fade-to-black at end if needed

---

## 4. Value Drop Techniques (Keep Eyes Moving)

### 4.1 Word Highlighting
Change color of keywords to draw attention.
```tsx
{ text: "important", color: '#FF6B6B' }
```

### 4.2 Word Jitters/Shake
Subtle movement on emphasis words.
```tsx
transform: `translate(${Math.sin(frame * 0.5) * 3}px, ${Math.sin(frame * 0.3) * 3}px)`
```

### 4.3 Color Palette for Words
- **Hook/Attention**: Gold (#FFD700), Red (#FF6B6B)
- **Positive/Action**: Green (#4ECDC4), Teal (#45B7D1)
- **Calm/Trust**: Blue (#96CEB4), Purple (#9B59B6)
- **Neutral**: White (#FFFFFF), Light Gray (#E0E0E0)

---

## 5. Animation Library

> **USE USER'S SPECIFIED ANIMATION IF PROVIDED.**
> These are fallbacks only.

### Entry Animations (when text appears)

| Name | Code | When to Use |
|------|------|-------------|
| **spring** | `spring({ frame: frame - start, fps, config: { damping: 100 } })` | Default, snappy entrance |
| **fadeIn** | `interpolate(frame, [start, start+15], [0, 1])` | Gentle, calm content |
| **scaleUp** | `interpolate(frame, [start, start+10], [0.5, 1])` | Impactful statements |
| **slideUp** | `interpolate(frame, [start, start+15], [50, 0])` for Y position | Lists, sequences |
| **slideLeft** | `interpolate(frame, [start, start+15], [100, 0])` for X | Reveals |

### Exit Animations (when text leaves)

| Name | Code |
|------|------|
| **fadeOut** | `interpolate(frame, [end-15, end], [1, 0])` |
| **scaleDown** | `interpolate(frame, [end-10, end], [1, 0.8])` |

### Emphasis Animations (during display)

| Name | Code | Effect |
|------|------|--------|
| **shake** | `translate(${Math.sin(frame*0.5)*3}px, ${Math.sin(frame*0.3)*3}px)` | Urgency, warning |
| **pulse** | `scale(${1 + Math.sin(frame*0.15)*0.08})` | Importance, CTA |
| **glow** | `textShadow: '0 0 20px rgba(R,G,B,0.8)'` | Highlight, magic |
| **bounce** | `translateY(${Math.sin(frame*0.2)*5}px)` | Playful, fun |
| **rotate** | `rotate(${Math.sin(frame*0.1)*2}deg)` | Attention, quirky |
| **explode** | `scale(${spring({frame: frame-start, fps:30, config:{damping:50}})})` | Impact, dramatic |

### Word Size Variations

When keywords have a `size` property, apply these font sizes:

| Size | Font Size | Use Case |
|------|-----------|----------|
| **huge** | 96px or larger | Single impact words like "WAIT", "STOP" |
| **large** | 72px | Important phrases |
| **normal** | 52px | Default body text |
| **small** | 36px | Subtle, quick words |

Example with size:
```tsx
parts: [
  { text: "One ", color: '#FFFFFF', size: 'normal' },
  { text: "small", color: '#4ECDC4', size: 'small' },  // smaller font
  { text: " habit", color: '#FFFFFF', size: 'normal' }
]
```

---

## 6. Keyword Structure (CRITICAL)

### ❌ WRONG - Don't do this
```tsx
// Keyword is NOT in the text, can't be found!
{ text: "You're not ", keyword: 'lazy' }
```

### ✅ CORRECT - Parts array
```tsx
// Each part has its own color and effects
{ 
  parts: [
    { text: "You're not ", color: '#FFFFFF' },
    { text: "lazy", color: '#FF6B6B', effect: 'shake' }
  ]
}
```

---

## 6.1 SPACING RULES (CRITICAL - READ CAREFULLY)

HTML collapses whitespace between inline elements. You MUST handle spacing correctly.

### ❌ WRONG - Spaces get collapsed
```tsx
// Trailing spaces get stripped, words touch!
parts: [
  { text: "Every ", color: '#FFFFFF' },    // ← space gets lost
  { text: "expert", color: '#45B7D1' },
  { text: " was once a ", color: '#FFFFFF' },
  { text: "beginner", color: '#96CEB4' }
]
// Result: "Everyexpertwas once abeginner" ← BROKEN!
```

### ✅ CORRECT - Use whiteSpace: 'pre' on spans
```tsx
// Add whiteSpace: 'pre' to preserve all spaces
<span style={{ color: part.color, whiteSpace: 'pre' }}>
  {part.text}
</span>
```

### ✅ ALSO CORRECT - Use &nbsp; or explicit space characters
```tsx
// Include non-breaking space entities
parts: [
  { text: "Every\u00A0", color: '#FFFFFF' },  // \u00A0 = non-breaking space
  { text: "expert", color: '#45B7D1' },
  { text: "\u00A0was once a\u00A0", color: '#FFFFFF' },
  { text: "beginner", color: '#96CEB4' }
]
```

### ✅ SIMPLEST - Keep full phrases, only split at keywords
```tsx
// DON'T over-split. Only separate at actual keywords.
parts: [
  { text: "Every ", color: '#FFFFFF' },
  { text: "expert", color: '#45B7D1' },  // keyword
  { text: " was once a ", color: '#FFFFFF' },  // keep full phrase
  { text: "beginner", color: '#96CEB4' }  // keyword
]
// AND add display: 'inline' + whiteSpace: 'pre' to spans!
```

### Required CSS for Spans
```tsx
<span style={{ 
  color: part.color,
  display: 'inline',
  whiteSpace: 'pre'  // ← CRITICAL: preserves spaces
}}>
  {part.text}
</span>
```

---

## 7. Timing Rules

| Duration | Frames | Use Case |
|----------|--------|----------|
| 1 second | 30 frames | Single word/phrase |
| 1.5 seconds | 45 frames | Short sentence |
| 2 seconds | 60 frames | Longer text |

Formula: `duration_seconds * 30 = frames`

---

## 8. Default Fallbacks

If user doesn't specify:
- **Entry animation**: spring
- **Exit animation**: fadeOut
- **Hook color**: #FFD700 (gold)
- **Keyword effect**: none (just color)
- **Background**: #0a0a0a
- **Text color**: #FFFFFF
- **Font size**: 72px hook, 52px body

---

## 9. Code Template

```tsx
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';

export const MyComposition = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const segments = [
    { 
      start: 0, 
      end: 30,
      entry: 'spring',      // or 'fadeIn', 'scaleUp', 'slideUp'
      parts: [
        { text: "Hook text", color: '#FFD700', effect: 'pulse' }
      ]
    },
    // ... more segments based on user's pacing
  ];

  // Apply entry animation based on segment.entry
  const getEntryAnimation = (type, start) => {
    switch(type) {
      case 'spring': return spring({ frame: frame - start, fps, config: { damping: 100 } });
      case 'fadeIn': return 1; // handled by opacity
      case 'scaleUp': return interpolate(frame, [start, start+10], [0.5, 1], { extrapolateRight: 'clamp' });
      default: return 1;
    }
  };

  return (
    <AbsoluteFill style={{ 
      backgroundColor: '#0a0a0a', 
      justifyContent: 'center', 
      alignItems: 'center',
      padding: '100px 80px 200px 80px'  // Safe zone
    }}>
      {/* Render segments */}
    </AbsoluteFill>
  );
};
```
