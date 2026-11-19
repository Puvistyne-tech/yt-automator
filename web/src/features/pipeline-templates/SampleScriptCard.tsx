import { SampleScriptView } from "@/features/pipeline-templates/SampleScriptView";
import {
  type SampleInput,
  type SampleScriptState,
  useSampleScript,
} from "@/features/pipeline-templates/useSampleScript";
import { Button, ButtonLink, Callout, Card, FormField, Input, Select, Spinner } from "@/shared/ui";

const TITLE = "Try a sample script";
const WRITING = "Writing a sample script";

function SampleControls({ state }: { state: SampleScriptState }) {
  return (
    <div className="sample-controls">
      <FormField label="Language" error={state.errors.language}>
        <Select
          value={state.language}
          options={state.languages.map((option) => ({ value: option.code, label: option.name }))}
          onChange={(event) => state.setLanguage(event.target.value)}
        />
      </FormField>
      <FormField
        label="Topic"
        hint="Optional. Leave it empty and the pipeline picks one."
        error={state.errors.topic}
      >
        <Input value={state.topic} onChange={(event) => state.setTopic(event.target.value)} />
      </FormField>
      <Button variant="primary" icon="play" loading={state.writing} onClick={state.write}>
        {state.writing ? "Writing…" : "Write a sample script"}
      </Button>
    </div>
  );
}

function UnavailableNotice({ message }: { message: string | null }) {
  if (message === null) {
    return null;
  }
  return (
    <Callout tone="info">
      <span>{message}</span>
      <ButtonLink to="/providers" size="sm">
        Open Providers
      </ButtonLink>
    </Callout>
  );
}

function WritingProgress() {
  return (
    <p className="row subtle" role="status" aria-label={WRITING}>
      <Spinner size={14} />
      {WRITING}. This can take a minute.
    </p>
  );
}

function SampleScriptCard({ state }: { state: SampleScriptState }) {
  return (
    <Card
      title={TITLE}
      aria-label={TITLE}
      description="Writes one script from this page as it is now, without saving anything. This is only the script: no pictures or voice are made."
    >
      <div className="stack">
        <SampleControls state={state} />
        {state.writing && <WritingProgress />}
        <UnavailableNotice message={state.unavailable} />
        {state.sample !== undefined && <SampleScriptView sample={state.sample} />}
      </div>
    </Card>
  );
}

export function SampleScriptPanel(props: SampleInput) {
  return <SampleScriptCard state={useSampleScript(props)} />;
}
