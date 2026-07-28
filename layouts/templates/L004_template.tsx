import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';

/**
 * Layout L004: CTA Pulse
 * 
 * Call-to-action ending with pulsing animation.
 * Large centered text with emphasis effects.
 * 
 * SLOTS:
 * - mainText: Main CTA text
 * - subText: Secondary text below
 * - emoji: Animated emoji
 * - mainColor: Color for main text
 * - pulseIntensity: Scale factor for pulse (1.0 to 1.3)
 */

// ============================================
// SLOT VALUES - AI FILLS THESE
// ============================================
const mainText = '{{MAIN_TEXT}}';
const subText = '{{SUB_TEXT}}';
const emoji = '{{EMOJI}}';
const mainColor = '{{MAIN_COLOR}}';
const pulseIntensity = {{PULSE_INTENSITY}};
// ============================================

export const CodeReel = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // Pulsing effect
  const pulsePhase = Math.sin(frame * 0.1) * 0.5 + 0.5; // 0 to 1
  const scale = 1 + (pulseIntensity - 1) * pulsePhase;
  
  // Emoji bounce
  const emojiY = Math.sin(frame * 0.15) * 10;
  
  // Entry animation
  const entryProgress = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 100 },
  });
  
  // Text entry
  const textOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });
  const textY = interpolate(frame, [0, 20], [30, 0], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '100px 60px',
    }}>
      {/* Main CTA Text */}
      <div style={{
        color: mainColor,
        fontSize: 72,
        fontWeight: 800,
        textAlign: 'center',
        transform: `scale(${scale}) translateY(${textY}px)`,
        opacity: textOpacity,
        textShadow: `0 0 30px ${mainColor}40`,
        letterSpacing: -1,
      }}>
        {mainText}
      </div>
      
      {/* Sub Text */}
      {subText && (
        <div style={{
          color: '#ffffff',
          fontSize: 36,
          fontWeight: 500,
          textAlign: 'center',
          marginTop: 20,
          opacity: interpolate(frame, [15, 35], [0, 0.8], { extrapolateRight: 'clamp' }),
        }}>
          {subText}
        </div>
      )}
      
      {/* Animated Emoji */}
      {emoji && (
        <div style={{
          fontSize: 80,
          marginTop: 40,
          transform: `translateY(${emojiY}px) scale(${entryProgress})`,
        }}>
          {emoji}
        </div>
      )}
      
      {/* Glow effect behind */}
      <div style={{
        position: 'absolute',
        width: 300,
        height: 300,
        borderRadius: '50%',
        background: `radial-gradient(circle, ${mainColor}30 0%, transparent 70%)`,
        opacity: pulsePhase * 0.5,
        zIndex: -1,
      }} />
    </AbsoluteFill>
  );
};
