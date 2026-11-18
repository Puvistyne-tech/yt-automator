import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { AppProviders, createQueryClient } from "@/app/AppProviders";
import { routes } from "@/app/routes";

export type User = ReturnType<typeof userEvent.setup>;

export function renderApp(route: string) {
  const client = createQueryClient(false);
  const router = createMemoryRouter(routes, { initialEntries: [route] });
  const navigateExternal = vi.fn<(url: string) => void>();
  const user = userEvent.setup();
  const { unmount } = render(
    <AppProviders client={client} navigateExternal={navigateExternal}>
      <RouterProvider router={router} />
    </AppProviders>,
  );
  return { user, router, client, navigateExternal, unmount };
}

export function pathOf(router: ReturnType<typeof createMemoryRouter>): string {
  return router.state.location.pathname;
}

export async function findDialog(name: string | RegExp) {
  return within(await screen.findByRole("dialog", { name }));
}

export async function confirmDialog(user: User, title: string | RegExp, button: string) {
  await user.click((await findDialog(title)).getByRole("button", { name: button }));
}

export async function cancelDialog(user: User, title: string | RegExp, button = "Cancel") {
  await user.click((await findDialog(title)).getByRole("button", { name: button }));
  expect(screen.queryByRole("dialog", { name: title })).not.toBeInTheDocument();
}

export async function findToast(text: string | RegExp) {
  const region = screen.getByRole("region", { name: "Notifications" });
  return within(region).findByText(text);
}

export async function findWithin(
  text: string | RegExp,
  ancestor: string,
  options: { selector?: string; container?: HTMLElement } = {},
) {
  const scope = options.container ? within(options.container) : screen;
  const match = await scope.findByText(
    text,
    options.selector === undefined ? {} : { selector: options.selector },
  );
  const found = match.closest<HTMLElement>(ancestor);
  if (found === null) {
    throw new Error(`No ${ancestor} contains ${String(text)}`);
  }
  return within(found);
}

export async function findRow(table: string, text: string | RegExp) {
  const grid = await screen.findByRole("table", { name: table });
  return findWithin(text, "tr", { container: grid });
}
