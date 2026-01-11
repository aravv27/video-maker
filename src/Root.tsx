import {Composition} from 'remotion';
import {MyComposition} from './Composition';

export const RemotionRoot: React.FC = () => {
	return (
		<>
			<Composition
				id="MyComp"
				component={MyComposition}
				durationInFrames={300}  // 10 seconds at 30fps
				fps={30}
				width={1080}
				height={1920}  // Vertical reel format
			/>
		</>
	);
};
