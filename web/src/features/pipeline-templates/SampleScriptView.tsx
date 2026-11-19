import { useId } from "react";
import type { SampleScene, SampleScript } from "@/api/types";
import { numberedScenes } from "@/features/pipeline-templates/model/preview";

function SceneItem({ scene }: { scene: SampleScene }) {
  return (
    <li className="sample-scene">
      {scene.heading !== "" && <h4 className="sample-scene-heading">{scene.heading}</h4>}
      <p>{scene.narration}</p>
      {scene.action !== "" && <p className="subtle">{scene.action}</p>}
    </li>
  );
}

function UploadText({ sample }: { sample: SampleScript }) {
  return (
    <dl className="sample-upload panel-inset panel-inset-muted">
      <dt className="subtle">YouTube title</dt>
      <dd>{sample.upload_title}</dd>
      <dt className="subtle">YouTube description</dt>
      <dd className="sample-description">{sample.upload_description}</dd>
    </dl>
  );
}

export function SampleScriptView({ sample }: { sample: SampleScript }) {
  const titleId = useId();
  return (
    <article className="sample-script" aria-labelledby={`${titleId}-kind ${titleId}`}>
      <header className="sample-script-head">
        <span className="subtle" id={`${titleId}-kind`}>
          Sample script
        </span>
        <h3 id={titleId}>{sample.title}</h3>
      </header>
      <ol className="sample-scenes" aria-label="Scenes">
        {numberedScenes(sample.scenes).map(({ number, scene }) => (
          <SceneItem key={number} scene={scene} />
        ))}
      </ol>
      {sample.takeaway !== "" && (
        <div className="sample-takeaway">
          <span className="subtle">Takeaway</span>
          <p>{sample.takeaway}</p>
        </div>
      )}
      <UploadText sample={sample} />
      <p className="subtle">Written by {sample.provider}.</p>
    </article>
  );
}
