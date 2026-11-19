import type { ReactNode } from "react";
import { ButtonLink } from "@/shared/ui/Button";
import { Spinner } from "@/shared/ui/Spinner";
import { Callout } from "@/shared/ui/surfaces";

export function ProgressLine({ label, children }: { label: string; children: ReactNode }) {
  return (
    <p className="row subtle" role="status" aria-label={label}>
      <Spinner size={14} />
      {children}
    </p>
  );
}

export function LinkCallout({
  message,
  to,
  action,
}: {
  message: string | null;
  to: string;
  action: string;
}) {
  if (message === null) {
    return null;
  }
  return (
    <Callout tone="info">
      <span>{message}</span>
      <ButtonLink to={to} size="sm">
        {action}
      </ButtonLink>
    </Callout>
  );
}
