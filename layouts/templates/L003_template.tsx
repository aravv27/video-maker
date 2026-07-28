import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';

/**
 * Layout L003: Split Explain
 * 
 * Split screen with code on left, explanation text on right.
 * Explanations sync with code line highlights.
 * 
 * SLOTS:
 * - code: Code snippet for left panel
 * - explanations: Array of {text, start, highlightLine}
 * - language: Programming language
 * - splitRatio: Left panel width ratio (0.3 to 0.7)
 */

interface Explanation {
  text: string;
  start: number;
  highlightLine: number;
}

// ============================================
// SLOT VALUES - AI FILLS THESE
// ============================================
const code = `{{CODE}}`;
const explanations: Explanation[] = {{EXPLANATIONS}};
const splitRatio = {{SPLIT_RATIO}};
// ============================================

export const CodeReel = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  const codeLines = code.split('\n');
  const secondsElapsed = frame / fps;
  
  // Find current explanation
  const currentExplanation = explanations
    .filter(e => secondsElapsed >= e.start)
    .pop();
  
  const highlightLine = currentExplanation?.highlightLine || -1;

  return (
    <AbsoluteFill style={{
      display: 'flex',
      flexDirection: 'row',
    }}>
      {/* Left Panel - Code */}
      <div style={{
        width: `${splitRatio * 100}%`,
        backgroundColor: '#1e1e1e',
        padding: '60px 30px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        overflow: 'hidden',
      }}>
        <div style={{
          fontFamily: '"Fira Code", "Consolas", monospace',
          fontSize: 22,
          lineHeight: 1.5,
        }}>
          {codeLines.map((line, index) => {
            const lineNumber = index + 1;
            const isHighlighted = lineNumber === highlightLine;
            
            return (
              <div
                key={index}
                style={{
                  display: 'flex',
                  backgroundColor: isHighlighted ? 'rgba(255, 215, 0, 0.15)' : 'transparent',
                  borderLeft: isHighlighted ? '3px solid #FFD700' : '3px solid transparent',
                  paddingLeft: 10,
                  marginLeft: -13,
                  transition: 'background-color 0.3s',
                }}
              >
                <span style={{
                  color: '#858585',
                  marginRight: 15,
                  minWidth: 25,
                  textAlign: 'right',
                }}>
                  {lineNumber}
                </span>
                <span style={{ color: '#d4d4d4' }}>
                  {line || ' '}
                </span>
              </div>
            );
          })}
        </div>
      </div>
      
      {/* Right Panel - Explanation */}
      <div style={{
        width: `${(1 - splitRatio) * 100}%`,
        backgroundColor: '#0a0a0a',
        padding: '60px 40px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
      }}>
        {currentExplanation && (
          <div style={{
            color: '#ffffff',
            fontSize: 36,
            fontWeight: 600,
            textAlign: 'center',
            lineHeight: 1.4,
            opacity: interpolate(
              frame,
              [currentExplanation.start * fps, currentExplanation.start * fps + 15],
              [0, 1],
              { extrapolateRight: 'clamp' }
            ),
          }}>
            {currentExplanation.text}
          </div>
        )}
        
        {/* Line indicator */}
        {highlightLine > 0 && (
          <div style={{
            marginTop: 30,
            color: '#FFD700',
            fontSize: 24,
            opacity: 0.7,
          }}>
            Line {highlightLine}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
