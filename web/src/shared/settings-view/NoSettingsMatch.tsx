import { Button, EmptyState } from "@/shared/ui";

export function NoSettingsMatch({
  onClear,
  hint = "Try another word, or turn off Changed only.",
}: {
  onClear: () => void;
  hint?: string;
}) {
  return (
    <EmptyState
      icon="inbox"
      title="No settings match"
      description={hint}
      action={
        <Button size="sm" onClick={onClear}>
          Clear search
        </Button>
      }
    />
  );
}
