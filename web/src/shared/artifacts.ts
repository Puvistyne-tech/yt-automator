export const FINAL_OUTPUT_KINDS: ReadonlySet<string> = new Set([
  "video",
  "thumbnail",
  "subtitle",
  "metadata",
]);

export interface OutputFile {
  kind: string;
  language: string | null;
}

export function isFinalOutput(artifact: OutputFile): boolean {
  return FINAL_OUTPUT_KINDS.has(artifact.kind) && artifact.language !== null;
}
