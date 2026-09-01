import "./index.css";
import { TechStoryComposition } from "./Composition";
import { ProductionTechStoryComposition } from "./ProductionComposition";
import { ReferenceFixtureCompositions } from "./ReferenceFixtures";
import { BankRunMasterComposition } from "./BankRunMasterComposition";
import { Vox3DMotionGraphicsTopHalfComposition } from "./Vox3DMotionGraphicsComposition";
import { FlowVideoExplainerTopHalfComposition } from "./FlowVideoExplainerComposition";
import { Vox0826TopHalfComposition } from "./Vox0826Composition";
import { VoxDioramaTopHalfComposition } from "./VoxDioramaComposition";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <TechStoryComposition />
      <ProductionTechStoryComposition />
      <ReferenceFixtureCompositions />
      <VoxDioramaTopHalfComposition />
      <Vox0826TopHalfComposition />
      <FlowVideoExplainerTopHalfComposition />
      <BankRunMasterComposition />
      <Vox3DMotionGraphicsTopHalfComposition />
    </>
  );
};
