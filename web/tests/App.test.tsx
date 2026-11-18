import { screen, within } from "@testing-library/react";
import { renderApp } from "./helpers/renderApp";

describe("App shell", () => {
  it("shows the product name and every main section in the sidebar", async () => {
    renderApp("/");

    expect(screen.getByText("AutoTube")).toBeInTheDocument();
    const nav = within(screen.getByRole("navigation", { name: "Main" }));
    for (const name of ["Dashboard", "Automations", "Runs", "Channels", "Providers", "Settings"]) {
      expect(nav.getByRole("link", { name: new RegExp(name) })).toBeInTheDocument();
    }
    expect(await screen.findByRole("heading", { level: 1, name: "Dashboard" })).toBeInTheDocument();
  });

  it.each([
    ["/runs", "Runs"],
    ["/channels", "Channels"],
    ["/providers", "Providers"],
    ["/settings", "Settings"],
    ["/automations", "Automations"],
  ])("renders %s with its page heading", async (route, heading) => {
    renderApp(route);

    expect(await screen.findByRole("heading", { level: 1, name: heading })).toBeInTheDocument();
  });

  it("shows a not found page for unknown routes", async () => {
    renderApp("/nowhere");

    expect(await screen.findByText("Page not found")).toBeInTheDocument();
  });
});
