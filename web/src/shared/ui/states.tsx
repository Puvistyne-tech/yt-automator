import type { ReactNode } from "react";
import { Button } from "@/shared/ui/Button";
import { Icon, type IconName } from "@/shared/ui/Icon";
import { LoadingState } from "@/shared/ui/Spinner";

export function EmptyState({
  icon = "inbox",
  title,
  description,
  action,
}: {
  icon?: IconName;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Icon name={icon} size={22} />
      </span>
      <h3>{title}</h3>
      {description !== undefined && <p className="muted">{description}</p>}
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Could not load this",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="error-state" role="alert">
      <span className="empty-icon error-icon">
        <Icon name="alert" size={22} />
      </span>
      <h3>{title}</h3>
      <p className="muted">{message}</p>
      {onRetry && (
        <Button size="sm" icon="refresh" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

interface QueryLike<T> {
  data: T | undefined;
  error: Error | null;
  isPending: boolean;
  refetch: () => unknown;
}

interface QueryStateProps<T> {
  query: QueryLike<T>;
  loadingLabel?: string;
  isEmpty?: (data: T) => boolean;
  empty?: ReactNode;
  children: (data: T) => ReactNode;
}

export function QueryState<T>({
  query,
  loadingLabel,
  isEmpty,
  empty,
  children,
}: QueryStateProps<T>) {
  if (query.isPending) {
    return <LoadingState {...(loadingLabel === undefined ? {} : { label: loadingLabel })} />;
  }
  if (query.error !== null || query.data === undefined) {
    return (
      <ErrorState
        message={query.error?.message ?? "No data was returned."}
        onRetry={() => void query.refetch()}
      />
    );
  }
  if (isEmpty?.(query.data) && empty !== undefined) {
    return <>{empty}</>;
  }
  return <>{children(query.data)}</>;
}
