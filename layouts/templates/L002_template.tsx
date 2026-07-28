import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';

/**
 * Layout L002: Code Reveal
 * 
 * Shows code snippet with lines revealing progressively.
 * Optional line highlighting for emphasis.
 * 
 * SLOTS:
 * - code: The code snippet string
 * - language: Programming language (for future syntax highlighting)
 * - highlightLines: Array of line numbers to highlight
 * - title: Optional title above code
 * - revealSpeed: Lines per second
 * - theme: "dark" or "light"
 */

// ============================================
// SLOT VALUES - AI FILLS THESE
// ============================================
const code = `{{CODE}}`;
const highlightLines: number[] = {{HIGHLIGHT_LINES}};
const title = '{{TITLE}}';
const revealSpeed = {{REVEAL_SPEED}};
const theme = '{{THEME}}';
// ============================================

export const CodeReel = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  const codeLines = code.split('\n');
  const secondsElapsed = frame / fps;
  const linesToShow = Math.floor(secondsElapsed * revealSpeed);
  
  const isDark = theme === 'dark';
  const bgColor = isDark ? '#1e1e1e' : '#f5f5f5';
  const textColor = isDark ? '#d4d4d4' : '#333333';
  const highlightBg = isDark ? 'rgba(255, 215, 0, 0.2)' : 'rgba(255, 215, 0, 0.3)';
  const lineNumberColor = isDark ? '#858585' : '#999999';

  return (
    <AbsoluteFill style={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '80px 40px',
    }}>
      {/* Title */}
      {title && (
        <div style={{
          color: isDark ? '#ffffff' : '#000000',
          fontSize: 48,
          fontWeight: 700,
          marginBottom: 30,
          opacity: interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' }),
        }}>
          {title}
        </div>
      )}
      
      {/* Code container */}
      <div style={{
        backgroundColor: bgColor,
        borderRadius: 16,
        padding: '30px 40px',
        width: '90%',
        maxWidth: 900,
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        fontFamily: '"Fira Code", "Consolas", monospace',
        fontSize: 28,
        lineHeight: 1.6,
      }}>
        {codeLines.map((line, index) => {
          const lineNumber = index + 1;
          const isVisible = index < linesToShow;
          const isHighlighted = highlightLines.includes(lineNumber);
          
          // Animate highlight
          const highlightOpacity = isHighlighted 
            ? interpolate(
                frame, 
                [index / revealSpeed * fps, index / revealSpeed * fps + 20], 
                [0, 1], 
                { extrapolateRight: 'clamp' }
              )
            : 0;
          
          if (!isVisible) return null;
          
          const lineOpacity = interpolate(
            frame,
            [(index / revealSpeed) * fps, (index / revealSpeed) * fps + 10],
            [0, 1],
            { extrapolateRight: 'clamp' }
          );
          
          return (
            <div
              key={index}
              style={{
                display: 'flex',
                opacity: lineOpacity,
                backgroundColor: isHighlighted ? highlightBg : 'transparent',
                marginLeft: -20,
                marginRight: -20,
                paddingLeft: 20,
                paddingRight: 20,
                borderLeft: isHighlighted ? '3px solid #FFD700' : '3px solid transparent',
              }}
            >
              <span style={{
                color: lineNumberColor,
                marginRight: 20,
                minWidth: 30,
                textAlign: 'right',
                userSelect: 'none',
              }}>
                {lineNumber}
              </span>
              <span style={{ color: textColor }}>
                {line || ' '}
              </span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
