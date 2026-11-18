import { useEffect } from "react";
import { useBlocker } from "react-router";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";

function useBeforeUnload(when: boolean) {
  useEffect(() => {
    if (!when) {
      return;
    }
    const handler = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [when]);
}

export function UnsavedChangesPrompt({ when }: { when: boolean }) {
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      when && currentLocation.pathname !== nextLocation.pathname,
  );
  useBeforeUnload(when);
  return (
    <ConfirmDialog
      open={blocker.state === "blocked"}
      title="Discard unsaved changes?"
      message="You have changes that are not saved. Leaving this page will discard them."
      confirmLabel="Discard changes"
      cancelLabel="Keep editing"
      onConfirm={() => blocker.proceed?.()}
      onCancel={() => blocker.reset?.()}
    />
  );
}
