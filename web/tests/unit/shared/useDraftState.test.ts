import { act, renderHook } from "@testing-library/react";
import { useDraftState } from "@/shared/hooks/useDraftState";

const renderDraft = () => renderHook(() => useDraftState({ name: "a" }, JSON.stringify));

describe("useDraftState", () => {
  it("is dirty after a change and clean after saving the current draft", () => {
    const { result } = renderDraft();
    expect(result.current.dirty).toBe(false);

    act(() => result.current.setDraft({ name: "b" }));
    expect(result.current.dirty).toBe(true);

    act(() => result.current.markSaved());
    expect(result.current).toMatchObject({ dirty: false, draft: { name: "b" } });
  });

  it("replaces the draft with what the server saved", () => {
    const { result } = renderDraft();
    act(() => result.current.setDraft({ name: " b " }));

    act(() => result.current.markSaved({ name: "b" }));

    expect(result.current).toMatchObject({ dirty: false, draft: { name: "b" } });
  });
});
