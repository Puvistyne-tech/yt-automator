import { useMutation } from "@tanstack/react-query";
import { act, renderHook, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { ApiError } from "@/api/errors";
import { useConfirmedMutation } from "@/api/useConfirmedMutation";
import { AppProviders, createQueryClient } from "@/app/AppProviders";
import { useConfirmTarget } from "@/shared/ui";

interface Item {
  id: string;
  name: string;
}

const ITEM: Item = { id: "item-1", name: "First" };

function wrapper({ children }: { children: ReactNode }) {
  return <AppProviders client={createQueryClient(false)}>{children}</AppProviders>;
}

function renderFlow(mutationFn: (id: string) => Promise<string>, onSuccess = vi.fn()) {
  return renderHook(
    () => {
      const confirm = useConfirmTarget<Item>();
      const mutation = useMutation({ mutationFn });
      const flow = useConfirmedMutation({
        confirm,
        mutation,
        vars: (item) => item.id,
        success: (item) => `Removed ${item.name}.`,
        onSuccess,
      });
      return { confirm, flow };
    },
    { wrapper },
  );
}

describe("useConfirmedMutation", () => {
  it("mutates the confirmed target, toasts, calls back and closes", async () => {
    const mutationFn = vi.fn((id: string) => Promise.resolve(`gone ${id}`));
    const onSuccess = vi.fn();
    const { result } = renderFlow(mutationFn, onSuccess);

    act(() => result.current.confirm.ask(ITEM));
    act(() => result.current.flow.onConfirm());

    expect(await screen.findByText("Removed First.")).toBeInTheDocument();
    expect(mutationFn.mock.calls[0]?.[0]).toBe("item-1");
    expect(onSuccess).toHaveBeenCalledWith("gone item-1", ITEM);
    await waitFor(() => expect(result.current.confirm.target).toBeNull());
    expect(result.current.flow.busy).toBe(false);
  });

  it("toasts the error and still closes the dialog", async () => {
    const failure = new ApiError(409, "conflict", "In use.");
    const { result } = renderFlow(() => Promise.reject(failure));

    act(() => result.current.confirm.ask(ITEM));
    act(() => result.current.flow.onConfirm());

    expect(await screen.findByText("In use.")).toBeInTheDocument();
    await waitFor(() => expect(result.current.confirm.target).toBeNull());
  });

  it("does nothing without a target", () => {
    const mutationFn = vi.fn((id: string) => Promise.resolve(id));
    const { result } = renderFlow(mutationFn);

    act(() => result.current.flow.onConfirm());

    expect(mutationFn).not.toHaveBeenCalled();
  });
});
