import "@/shared/styles/tokens.css";
import "@/shared/styles/base.css";
import "@/shared/ui/controls.css";
import "@/shared/ui/surfaces.css";
import "@/shared/ui/overlay.css";
import "@/shared/ui/choices.css";
import "@/app/layout.css";
import { useState } from "react";
import { createBrowserRouter, RouterProvider } from "react-router";
import { AppProviders, createQueryClient } from "@/app/AppProviders";
import { routes } from "@/app/routes";

export function App() {
  const [client] = useState(() => createQueryClient());
  const [router] = useState(() => createBrowserRouter(routes));
  return (
    <AppProviders client={client}>
      <RouterProvider router={router} />
    </AppProviders>
  );
}
