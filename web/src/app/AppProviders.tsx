import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { ApiError } from "@/api/errors";
import {
  type ExternalNavigate,
  ExternalNavigationContext,
} from "@/shared/hooks/externalNavigation";
import { ToastProvider } from "@/shared/ui";

function shouldRetry(failureCount: number, error: Error): boolean {
  const clientError = error instanceof ApiError && error.status >= 400 && error.status < 500;
  return !clientError && failureCount < 2;
}

export function createQueryClient(retry = true): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: retry ? shouldRetry : false,
        staleTime: 10_000,
        refetchOnWindowFocus: true,
      },
      mutations: { retry: false },
    },
  });
}

interface AppProvidersProps {
  client: QueryClient;
  navigateExternal?: ExternalNavigate;
  children: ReactNode;
}

export function AppProviders({ client, navigateExternal, children }: AppProvidersProps) {
  const content = (
    <QueryClientProvider client={client}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>
  );
  return navigateExternal === undefined ? (
    content
  ) : (
    <ExternalNavigationContext.Provider value={navigateExternal}>
      {content}
    </ExternalNavigationContext.Provider>
  );
}
