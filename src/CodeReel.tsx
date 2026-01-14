import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';

// Fixed template - no AI generation needed
// Just edit the 'lines' array below with your content

interface Line {
  text: string;
  start: number;  // Start time in seconds
  color: string;
  isHook: boolean;
}

export const CodeReel = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ========================================
  // EDIT YOUR CONTENT HERE
  // ========================================
  const lines: Line[] = [
    { text: "Your skin deserves better.", start: 0, color: '#8B4557', isHook: true },
    { text: "Stop hiding.", start: 2, color: '#2D3436', isHook: false },
    { text: "Start glowing.", start: 3.5, color: '#B8860B', isHook: false },
    { text: "3 ingredients.", start: 5, color: '#2D3436', isHook: false },
    { text: "Zero chemicals.", start: 6.5, color: '#1E8449', isHook: false },
    { text: "Try it today.", start: 8, color: '#C71585', isHook: false },
  ];
  // ========================================

  const charsPerSecond = 20;

  return (
    <AbsoluteFill style={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '150px 60px',
      fontFamily: '"Playfair Display", Georgia, serif',
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
              fontSize: line.isHook ? '72px' : '56px',
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