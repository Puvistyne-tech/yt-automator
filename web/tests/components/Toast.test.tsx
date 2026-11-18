import { act, fireEvent, render, screen } from "@testing-library/react";
import { ToastProvider, useToast } from "@/shared/ui";

const onGo = vi.fn<() => void>();

function Trigger({ withAction }: { withAction: boolean }) {
  const toast = useToast();
  const show = () =>
    withAction ? toast.success("Queued.", { label: "Go", onClick: onGo }) : toast.success("Saved.");
  return (
    <button type="button" onClick={show}>
      Show
    </button>
  );
}

function showToast(withAction: boolean) {
  render(
    <ToastProvider>
      <Trigger withAction={withAction} />
    </ToastProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Show" }));
}

beforeEach(() => {
  onGo.mockClear();
  vi.useFakeTimers();
});

afterEach(() => vi.useRealTimers());

describe("Toast", () => {
  it("closes a plain toast after five seconds", () => {
    showToast(false);
    expect(screen.getByText("Saved.")).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(5000));

    expect(screen.queryByText("Saved.")).not.toBeInTheDocument();
  });

  it("keeps a toast with an action open until it is used", () => {
    showToast(true);

    act(() => vi.advanceTimersByTime(60_000));
    expect(screen.getByRole("button", { name: "Go" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Go" }));

    expect(onGo).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Queued.")).not.toBeInTheDocument();
  });

  it("closes a toast with an action when it is dismissed, without running the action", () => {
    showToast(true);

    fireEvent.click(screen.getByRole("button", { name: "Dismiss notification" }));

    expect(screen.queryByRole("button", { name: "Go" })).not.toBeInTheDocument();
    expect(onGo).not.toHaveBeenCalled();
  });
});
