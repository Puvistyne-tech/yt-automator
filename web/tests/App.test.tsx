import { render, screen } from "@testing-library/react";
import { App } from "@/app/App";

describe("App", () => {
  it("shows the product name as the page heading", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { level: 1, name: "YouTube Automator" }),
    ).toBeInTheDocument();
  });
});
