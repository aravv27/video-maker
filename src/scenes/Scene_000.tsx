import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';

interface Line {
  text: string;
  start: number;
  color: string;
  isHook: boolean;
}

const lines: Line[] = [
  { text: "Your skin deserves better.", start: 0.0, color: "#000000", isHook: true },
  { text: "Stop hiding.", start: 2.0, color: "#000000", isHook: false },
  { text: "Start glowing.", start: 3.5, color: "#000000", isHook: false },
  { text: "3 ingredients.", start: 5.0, color: "#000000", isHook: false },
  { text: "Zero chemicals.", start: 6.5, color: "#000000", isHook: false },
  { text: "Try it today.", start: 8.0, color: "#000000", isHook: false }
];
const charsPerSecond = 20;
const fontFamily = "\"Playfair Display\", Georgia, serif";
const hookFontSize = 72;
const bodyFontSize = 56;

export const Scene_000 = () => {
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