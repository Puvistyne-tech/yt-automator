import type { RouteObject } from "react-router";
import { Layout } from "@/app/Layout";
import { AutomationsPage } from "@/pages/AutomationsPage";
import { ChannelsPage } from "@/pages/ChannelsPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { RunDetailPage } from "@/pages/RunDetailPage";
import { RunsPage } from "@/pages/RunsPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { LoadingState } from "@/shared/ui";

const pageLoading = <LoadingState label="Loading page" />;

const editorRoute = async () => ({
  Component: (await import("@/pages/AutomationEditorPage")).AutomationEditorPage,
});

const providersRoute = async () => ({
  Component: (await import("@/pages/ProvidersPage")).ProvidersPage,
});

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "automations", element: <AutomationsPage /> },
      { path: "automations/new", lazy: editorRoute, hydrateFallbackElement: pageLoading },
      { path: "automations/:id", lazy: editorRoute, hydrateFallbackElement: pageLoading },
      { path: "runs", element: <RunsPage /> },
      { path: "runs/:id", element: <RunDetailPage /> },
      { path: "channels", element: <ChannelsPage /> },
      { path: "providers", lazy: providersRoute, hydrateFallbackElement: pageLoading },
      { path: "settings", element: <SettingsPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
