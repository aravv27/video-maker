import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';

interface Part {
  text: string;
  color: string;
  effect?: string;
  size?: string;
}

interface Segment {
  start: number;
  end: number;
  entry: string;
  parts: Part[];
}

export const MyComposition = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const segments: Segment[] = [
    {
      start: 0,
      end: 60,
      entry: 'scaleUp',
      parts: [
        { text: "WAIT.", color: '#FF0000', effect: 'explode', size: 'huge' }
      ]
    },
    {
      start: 60,
      end: 120,
      entry: 'scaleUp',
      parts: [
        { text: "This changes ", color: '#FFFFFF' },
        { text: "EVERYTHING", color: '#FFD700', effect: 'scale', size: 'large' },
        { text: ".", color: '#FFFFFF' }
      ]
    },
    {
      start: 120,
      end: 180,
      entry: 'scaleUp',
      parts: [
        { text: "One ", color: '#FFFFFF' },
        { text: "small", color: '#4ECDC4', size: 'small' },
        { text: " habit.", color: '#FFFFFF' }
      ]
    },
    {
      start: 180,
      end: 240,
      entry: 'scaleUp',
      parts: [
        { text: "MASSIVE ", color: '#FF6B6B', effect: 'explode', size: 'huge' },
        { text: "results.", color: '#FFFFFF' }
      ]
    },
    {
      start: 240,
      end: 300,
      entry: 'scaleUp',
      parts: [
        { text: "5 minutes", color: '#96CEB4', effect: 'pulse' },
        { text: " a day. That's ", color: '#FFFFFF' },
        { text: "all it takes", color: '#45B7D1', effect: 'glow' },
        { text: ".", color: '#FFFFFF' }
      ]
    }
  ];

  const getEffectStyle = (effect: string | undefined, frame: number): React.CSSProperties => {
    switch (effect) {
      case 'explode':
        return {
          transform: `scale(${spring({ frame: frame - (segments.find(s => s.parts.some(p => p.effect === 'explode'))?.start || 0), fps, config: { damping: 50 } })})`
        };
      case 'scale':
        return {
          transform: `scale(${1 + Math.sin(frame * 0.1) * 0.05})`
        };
      case 'pulse':
        return {
          transform: `scale(${1 + Math.sin(frame * 0.15) * 0.08})`
        };
      case 'glow':
        return {
          textShadow: '0 0 20px rgba(69, 183, 209, 0.8)'
        };
      default:
        return {};
    }
  };

  const getSize = (size: string | undefined): string => {
    switch (size) {
      case 'huge': return '96px';
      case 'large': return '72px';
      case 'small': return '36px';
      default: return '52px';
    }
  };

  const getEntryAnimation = (type: string, start: number): number => {
    switch (type) {
      case 'spring': return spring({ frame: frame - start, fps, config: { damping: 100 } });
      case 'scaleUp': return interpolate(frame, [start, start + 10], [0.5, 1], { extrapolateRight: 'clamp' });
      default: return 1;
    }
  };

  const getOpacity = (start: number, end: number): number => {
    if (frame < start) return 0;
    if (frame > end) return 0;
    if (frame < start + 15) return interpolate(frame, [start, start + 15], [0, 1]);
    if (frame > end - 15) return interpolate(frame, [end - 15, end], [1, 0]);
    return 1;
  };

  return (
    <AbsoluteFill style={{
      backgroundColor: '#1a1a2e',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '100px 80px 200px 80px',
      fontFamily: 'Arial, sans-serif'
    }}>
      {segments.map((segment, index) => {
        if (frame < segment.start || frame > segment.end) return null;

        const scale = getEntryAnimation(segment.entry, segment.start);
        const opacity = getOpacity(segment.start, segment.end);

        return (
          <div key={index} style={{
            opacity,
            transform: `scale(${scale})`,
            textAlign: 'center',
            fontSize: '52px',
            lineHeight: '1.2',
            whiteSpace: 'pre-wrap'
          }}>
            {segment.parts.map((part, partIndex) => (
              <span
                key={partIndex}
                style={{
                  color: part.color,
                  fontSize: getSize(part.size),
                  display: 'inline',
                  whiteSpace: 'pre',
                  ...getEffectStyle(part.effect, frame)
                }}
              >
                {part.text}
              </span>
            ))}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};