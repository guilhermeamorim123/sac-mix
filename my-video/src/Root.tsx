import "./index.css";
import { Composition } from "remotion";
import { KeylightDemo } from "./KeylightDemo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="KeylightDemo"
        component={KeylightDemo}
        durationInFrames={900}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{}}
      />
    </>
  );
};
