import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';

/**
 * Layout L001: Hook + Typewriter
 * 
 * Text stacks vertically. First line (hook) fades in large,
 * remaining lines typewrite character by character and stay on screen.
 * 
 * SLOTS:
 * - lines: Array of {text, start, color, isHook}
 * - charsPerSecond: Typewriter speed (default: 20)
 * - fontFamily: CSS font-family
 * - hookFontSize: Font size for hook (default: 72)
 * - bodyFontSize: Font size for body (default: 56)
 */

interface Line {
  text: string;
  start: number;
  color: string;
  isHook: boolean;
}

// ============================================
// SLOT VALUES - AI FILLS THESE
// ============================================
const lines: Line[] = {{LINES}};
const charsPerSecond = {{CHARS_PER_SECOND}};
const fontFamily = '{{FONT_FAMILY}}';
const hookFontSize = {{HOOK_FONT_SIZE}};
const bodyFontSize = {{BODY_FONT_SIZE}};
// ============================================

export const CodeReel = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '150px 60px',
      fontFamily: fontFamily,
      fontWeight: 700,
    }}>
      {lines.map((line, index) => {
        const startFrame = line.start * fps;
        
        if (frame < startFrame) return null;
        
        const framesSinceStart = frame - startFrame;
        const secondsSinceStart = framesSinceStart / fps;
        
        let displayText: string;
        let opacity: number;
        let scale: number;
        
        if (line.isHook) {
          displayText = line.text;
          opacity = interpolate(frame, [startFrame, startFrame + 15], [0, 1], { extrapolateRight: 'clamp' });
          scale = interpolate(frame, [startFrame, startFrame + 15], [0.9, 1], { extrapolateRight: 'clamp' });
        } else {
          const charsToShow = Math.floor(secondsSinceStart * charsPerSecond);
          displayText = line.text.slice(0, Math.min(charsToShow, line.text.length));
          opacity = displayText.length > 0 ? 1 : 0;
          scale = 1;
        }

        const showCursor = !line.isHook && displayText.length < line.text.length;

        return (
          <div
            key={index}
            style={{
              opacity,
              transform: `scale(${scale})`,
              color: line.color,
              fontSize: line.isHook ? hookFontSize : bodyFontSize,
              textAlign: 'center',
              lineHeight: 1.3,
              marginBottom: '15px',
              textShadow: '1px 1px 4px rgba(0,0,0,0.2)',
            }}
          >
            {displayText}
            {showCursor && (
              <span style={{ opacity: Math.sin(frame * 0.3) > 0 ? 1 : 0 }}>|</span>
            )}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
