import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useStoredChoice } from "@/shared/hooks/useStoredChoice";

const KEY = "test.choice";
const parse = (stored: string | null) => (stored === "b" ? "b" : "a");

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
});

describe("useStoredChoice", () => {
  it("starts from the stored value and remembers a new choice", () => {
    window.localStorage.setItem(KEY, "b");
    const { result } = renderHook(() => useStoredChoice(KEY, parse));
    expect(result.current[0]).toBe("b");
    act(() => result.current[1]("a"));
    expect(result.current[0]).toBe("a");
    expect(window.localStorage.getItem(KEY)).toBe("a");
  });

  it("keeps working when storage is unavailable", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const { result } = renderHook(() => useStoredChoice(KEY, parse));
    expect(result.current[0]).toBe("a");
    act(() => result.current[1]("b"));
    expect(result.current[0]).toBe("b");
  });
});
