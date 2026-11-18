import { useState } from "react";
import { useImportAutomation, usePreviewImport } from "@/api/automations";
import type { Automation, ImportPreview, JsonObject } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import {
  channelMapFrom,
  type ImportProblem,
  importProblem,
  parseExportFile,
} from "@/features/automation-list/importModel";

const NO_PROBLEM: ImportProblem = { message: null, channels: {}, fields: [] };

interface ImportState {
  open: boolean;
  fileName: string;
  document: JsonObject | null;
  preview: ImportPreview | null;
  choices: Record<string, string>;
  problem: ImportProblem;
}

const CLOSED: ImportState = {
  open: false,
  fileName: "",
  document: null,
  preview: null,
  choices: {},
  problem: NO_PROBLEM,
};

type Patch = (next: Partial<ImportState>) => void;

function useFileStep(patch: Patch) {
  const previewer = usePreviewImport();
  const check = (document: JsonObject) =>
    previewer.mutate(
      { document, channel_map: {} },
      {
        onSuccess: (preview) => patch({ preview }),
        onError: (error) => patch({ problem: importProblem(error) }),
      },
    );
  const choose = async (file: File) => {
    const parsed = parseExportFile(await file.text());
    const fresh = { fileName: file.name, preview: null, choices: {}, document: null };
    if ("error" in parsed) {
      patch({ ...fresh, problem: { ...NO_PROBLEM, message: parsed.error } });
      return;
    }
    patch({ ...fresh, document: parsed.document, problem: NO_PROBLEM });
    check(parsed.document);
  };
  return { choose, checking: previewer.isPending };
}

function useSubmitStep(state: ImportState, patch: Patch, close: () => void) {
  const importer = useImportAutomation();
  const notifier = useMutationNotifier();
  const send = (document: JsonObject) =>
    importer.mutate(
      { document, channel_map: channelMapFrom(state.choices) },
      {
        onSuccess: (created: Automation) => {
          close();
          notifier.succeed(`Imported “${created.name}”. It stays off until you enable it.`);
        },
        onError: (error) => patch({ problem: importProblem(error) }),
      },
    );
  const document = state.document;
  return {
    submit: document === null || state.preview === null ? undefined : () => send(document),
    importing: importer.isPending,
  };
}

export function useImportFlow() {
  const [state, setState] = useState(CLOSED);
  const patch: Patch = (next) => setState((current) => ({ ...current, ...next }));
  const close = () => setState(CLOSED);
  const file = useFileStep(patch);
  const submitStep = useSubmitStep(state, patch, close);
  return {
    ...state,
    ...file,
    ...submitStep,
    ask: () => setState({ ...CLOSED, open: true }),
    close,
    setChoice: (channelId: string, value: string) => {
      const { [channelId]: _answered, ...channels } = state.problem.channels;
      patch({
        choices: { ...state.choices, [channelId]: value },
        problem: { ...state.problem, channels },
      });
    },
  };
}

export type ImportFlow = ReturnType<typeof useImportFlow>;
