import { useId } from "react";
import { useChannels } from "@/api/channels";
import type { ExportedChannel, ImportPreview, PipelineDescriptor } from "@/api/types";
import {
  CHOOSE_CHANNEL,
  channelChoiceOptions,
  exportedChannelName,
  IMPORT_FILE_TYPES,
} from "@/features/automation-list/importModel";
import { pipelineName } from "@/features/automation-list/summary";
import type { ImportFlow } from "@/features/automation-list/useImportFlow";
import { AlertCallout, FormDialog, FormField, Input, Select } from "@/shared/ui";

function FilePicker({ flow }: { flow: ImportFlow }) {
  return (
    <FormField
      label="Export file"
      hint="A .json file saved with Export. Settings, languages, schedule, review and retry rules and targets are imported; secrets never are."
    >
      <Input
        type="file"
        className="import-file"
        accept={IMPORT_FILE_TYPES}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file !== undefined) {
            void flow.choose(file);
          }
        }}
      />
    </FormField>
  );
}

function ChannelChoice({ flow, channel }: { flow: ImportFlow; channel: ExportedChannel }) {
  const channels = useChannels();
  return (
    <FormField
      label={`Channel for “${exportedChannelName(channel)}”`}
      hint="This channel is not connected here. Pick one of yours, or leave its targets out."
      error={flow.problem.channels[channel.id]}
    >
      <Select
        value={flow.choices[channel.id] ?? CHOOSE_CHANNEL}
        placeholder="Choose a channel"
        options={channelChoiceOptions(channels.data ?? [])}
        onChange={(event) => flow.setChoice(channel.id, event.target.value)}
      />
    </FormField>
  );
}

function PreviewSummary({
  preview,
  pipelines,
}: {
  preview: ImportPreview;
  pipelines: PipelineDescriptor[];
}) {
  const { automation } = preview;
  const targets =
    automation.targets.length === 1 ? "1 target" : `${automation.targets.length} targets`;
  return (
    <p className="import-summary">
      Creates <strong>“{automation.name}”</strong> (
      {pipelineName(pipelines, automation.pipeline_type)}, {targets}), switched off.
    </p>
  );
}

function Problems({ flow }: { flow: ImportFlow }) {
  const listId = useId();
  const { message, fields } = flow.problem;
  return (
    <>
      {message !== null && (
        <AlertCallout tone="danger" role="alert">
          {message}
        </AlertCallout>
      )}
      {fields.length > 0 && (
        <div className="import-problems" role="alert" aria-labelledby={listId}>
          <p id={listId} className="field-error">
            This file cannot be imported as it is:
          </p>
          <ul>
            {fields.map((field) => (
              <li key={field.label}>
                <strong>{field.label}</strong>: {field.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

export function ImportDialog({
  flow,
  pipelines,
}: {
  flow: ImportFlow;
  pipelines: PipelineDescriptor[];
}) {
  return (
    <FormDialog
      open={flow.open}
      title="Import automation"
      description="Creates a switched-off copy from an AutoTube export, so nothing runs by surprise."
      submitLabel="Import automation"
      submitIcon="upload"
      busy={flow.importing || flow.checking}
      submitDisabled={flow.submit === undefined}
      onSubmit={() => flow.submit?.()}
      onClose={flow.close}
    >
      <div className="import-dialog">
        <FilePicker flow={flow} />
        <Problems flow={flow} />
        {flow.preview && <PreviewSummary preview={flow.preview} pipelines={pipelines} />}
        {flow.preview?.unknown_channels.map((channel) => (
          <ChannelChoice key={channel.id} flow={flow} channel={channel} />
        ))}
      </div>
    </FormDialog>
  );
}
