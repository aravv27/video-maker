import { AbsoluteFill, Img, Audio, staticFile, Sequence, useVideoConfig, getStaticFiles } from 'remotion';
import { CodeReel } from './CodeReel';

export const MyComposition = () => {
  const { fps } = useVideoConfig();
  
  // Get all audio files from public/audio folder
  const staticFiles = getStaticFiles();
  const audioFiles = staticFiles
    .filter(f => f.src.startsWith('audio/segment_') && f.src.endsWith('.mp3'))
    .sort((a, b) => a.src.localeCompare(b.src));
  
  // Calculate start times based on pacing (2s, 3.5s, 5s, 6.5s, 8s, etc.)
  const startTimes = [0, 2, 3.5, 5, 6.5, 8];
  
  return (
    <AbsoluteFill>
      <Img 
        src={staticFile('background/background_leaf_beige.jpg')}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover'
        }}
      />
      
      {/* Audio segments - each starts at specified time */}
      {audioFiles.map((file, index) => (
        <Sequence key={index} from={Math.round((startTimes[index] || index * 2) * fps)}>
          <Audio src={staticFile(file.src)} />
        </Sequence>
      ))}
      
      <CodeReel />
    </AbsoluteFill>
  );
};