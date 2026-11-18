import { ButtonLink, EmptyState } from "@/shared/ui";

export function NotFoundPage() {
  return (
    <EmptyState
      icon="alert"
      title="Page not found"
      description="The page you opened does not exist."
      action={
        <ButtonLink to="/" variant="primary">
          Go to dashboard
        </ButtonLink>
      }
    />
  );
}
