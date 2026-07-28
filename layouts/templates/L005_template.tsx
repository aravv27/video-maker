import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';

/**
 * Layout L005: Quote Centered
 * 
 * Single impactful quote centered on screen.
 * Elegant fade-in with optional attribution.
 * 
 * SLOTS:
 * - quote: The main quote text
 * - attribution: Attribution text (e.g., "— Steve Jobs")
 * - quoteColor: Color for quote
 * - fontSize: Font size for quote
 * - showQuoteMarks: Show decorative quote marks
 */

// ============================================
// SLOT VALUES - AI FILLS THESE
// ============================================
const quote = '{{QUOTE}}';
const attribution = '{{ATTRIBUTION}}';
const quoteColor = '{{QUOTE_COLOR}}';
const fontSize = {{FONT_SIZE}};
const showQuoteMarks = {{SHOW_QUOTE_MARKS}};
// ============================================

export const CodeReel = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // Quote fade in
  const quoteOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const quoteScale = interpolate(frame, [0, 30], [0.95, 1], { extrapolateRight: 'clamp' });
  
  // Attribution appears after quote
  const attributionOpacity = interpolate(frame, [45, 60], [0, 0.7], { extrapolateRight: 'clamp' });
  
  // Quote marks animation
  const quoteMarkOpacity = interpolate(frame, [10, 25], [0, 0.2], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '120px 80px',
    }}>
      {/* Decorative quote marks */}
      {showQuoteMarks && (
        <>
          <div style={{
            position: 'absolute',
            top: '25%',
            left: '10%',
            fontSize: 200,
            color: quoteColor,
            opacity: quoteMarkOpacity,
            fontFamily: 'Georgia, serif',
            lineHeight: 1,
          }}>
            "
          </div>
          <div style={{
            position: 'absolute',
            bottom: '25%',
            right: '10%',
            fontSize: 200,
            color: quoteColor,
            opacity: quoteMarkOpacity,
            fontFamily: 'Georgia, serif',
            lineHeight: 1,
            transform: 'rotate(180deg)',
          }}>
            "
          </div>
        </>
      )}
      
      {/* Main Quote */}
      <div style={{
        color: quoteColor,
        fontSize: fontSize,
        fontWeight: 600,
        textAlign: 'center',
        lineHeight: 1.3,
        opacity: quoteOpacity,
        transform: `scale(${quoteScale})`,
        fontFamily: '"Playfair Display", Georgia, serif',
        fontStyle: 'italic',
        maxWidth: '85%',
      }}>
        {quote}
      </div>
      
      {/* Attribution */}
      {attribution && (
        <div style={{
          color: '#ffffff',
          fontSize: 28,
          fontWeight: 400,
          marginTop: 40,
          opacity: attributionOpacity,
          fontFamily: 'system-ui, sans-serif',
        }}>
          {attribution}
        </div>
      )}
    </AbsoluteFill>
  );
};
