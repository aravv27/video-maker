# Design Principles for Remotion Video Generation

> Simple, clean cosmetics daily content style.

---

## Core Concept: STACKING TEXT + TYPEWRITER

Each line of text appears and **STAYS on screen**. Text accumulates vertically:

- **Hook**: Fades in instantly (no typewriter)
- **Other lines**: Type character by character with blinking cursor

---

## Code Structure

### Lines Array
```tsx
const lines = [
  { text: "Your hook here.", start: 0, color: '#FFB5C5', isHook: true },
  { text: "Second line.", start: 2, color: '#FFFFFF', isHook: false },
  { text: "Third line.", start: 4, color: '#FFD700', isHook: false },
];
```

### Key Rules
1. **Lines DON'T vanish** - once they appear, they stay
2. **Hook is bigger** - first line uses larger font (72px vs 56px)
3. **Hook fades in** - smooth opacity + scale animation
4. **Other lines typewrite** - characters appear one by one
5. **Blinking cursor** - shows during typewriter effect
6. **Stacked vertically** - flexbox column layout

---

## Typewriter Effect

```tsx
// Speed: 20 characters per second
const charsPerSecond = 20;

const framesSinceStart = frame - startFrame;
const secondsSinceStart = framesSinceStart / fps;
const charsToShow = Math.floor(secondsSinceStart * charsPerSecond);
const displayText = line.text.slice(0, charsToShow);
```

---

## Styling

### Font
Use CSS fonts:
```tsx
fontFamily: '"Playfair Display", Georgia, serif'
fontWeight: 700
```

### Colors (DARK for light backgrounds)
- Hook: Dark rose (#8B4557) or Dark gold (#B8860B)
- Body: Charcoal (#2D3436) or Dark brown (#5D4037)
- Accent: Forest green (#1E8449), Deep pink (#C71585)

> **Important**: Background is light, so use DARK text colors for readability!

---

## Timing

- Each line ~1.5-2 seconds apart
- Typewriter speed: ~20 chars/second
- Total duration = number of lines × ~2 seconds
