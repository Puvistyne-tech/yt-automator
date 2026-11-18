import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { AppProviders, createQueryClient } from "@/app/AppProviders";
import { routes } from "@/app/routes";

export function renderApp(route: string) {
  const client = createQueryClient(false);
  const router = createMemoryRouter(routes, { initialEntries: [route] });
  const navigateExternal = vi.fn<(url: string) => void>();
  const user = userEvent.setup();
  render(
    <AppProviders client={client} navigateExternal={navigateExternal}>
      <RouterProvider router={router} />
    </AppProviders>,
  );
  return { user, router, client, navigateExternal };
}

export function pathOf(router: ReturnType<typeof createMemoryRouter>): string {
  return router.state.location.pathname;
}

export async function findDialog(name: string | RegExp) {
  return within(await screen.findByRole("dialog", { name }));
}

export async function findToast(text: string | RegExp) {
  const region = screen.getByRole("region", { name: "Notifications" });
  return within(region).findByText(text);
}

export async function findRow(table: string, text: string | RegExp) {
  const grid = await screen.findByRole("table", { name: table });
  const cell = await within(grid).findByText(text);
  const row = cell.closest("tr");
  if (row === null) {
    throw new Error(`No row contains ${String(text)}`);
  }
  return within(row);
}
