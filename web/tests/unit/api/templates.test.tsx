import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { ApiError, fieldErrorsOf, normalizeFieldErrors } from "@/api/errors";
import { db } from "@/api/mocks/db";
import { templateConflictOf } from "@/api/templateErrors";
import {
  useDeleteTemplate,
  useDuplicateTemplate,
  useSaveTemplate,
  useTemplate,
  useTemplateEngines,
  useTemplates,
} from "@/api/templates";
import type { TemplateInput } from "@/api/types";
import { AppProviders, createQueryClient } from "@/app/AppProviders";

function wrapper({ children }: { children: ReactNode }) {
  return <AppProviders client={createQueryClient(false)}>{children}</AppProviders>;
}

const INPUT: TemplateInput = {
  engine: "narrated_video",
  name: "Ocean wonders",
  description: "",
  audience: "general",
  status: "draft",
  definition: { brief: "Short films about the sea." },
};

async function rejectionOf(run: () => Promise<unknown>): Promise<unknown> {
  try {
    await run();
  } catch (error) {
    return error;
  }
  throw new Error("expected a rejection");
}

describe("templateConflictOf", () => {
  it.each(["template_builtin", "template_in_use", "template_type_taken"])(
    "reads the %s conflict with the server message",
    (code) => {
      const error = new ApiError(409, code, "the server says why");
      expect(templateConflictOf(error)).toEqual({ code, message: "the server says why" });
    },
  );

  it.each([
    new ApiError(409, "channel_in_use", "other"),
    new ApiError(400, "template_in_use", "not a conflict status"),
    new Error("plain"),
    null,
  ])("ignores %s", (error) => {
    expect(templateConflictOf(error)).toBeNull();
  });
});

describe("template query hooks", () => {
  it("lists engines and templates, built-ins first, and reads one by id", async () => {
    const engines = renderHook(() => useTemplateEngines(), { wrapper });
    const list = renderHook(() => useTemplates(), { wrapper });
    const one = renderHook(() => useTemplate("space-facts"), { wrapper });

    await waitFor(() => expect(list.result.current.data).toBeDefined());
    await waitFor(() => expect(engines.result.current.data).toHaveLength(1));
    await waitFor(() => expect(one.result.current.data?.name).toBe("Space facts"));
    expect(list.result.current.data?.map((t) => t.builtin)).toEqual([true, false, false]);
  });

  it("does not fetch a template without an id", () => {
    const one = renderHook(() => useTemplate(undefined), { wrapper });
    expect(one.result.current.fetchStatus).toBe("idle");
  });
});

describe("template mutation hooks", () => {
  it("creates, then updates, a template", async () => {
    const create = renderHook(() => useSaveTemplate(undefined), { wrapper });
    const created = await act(() => create.result.current.mutateAsync(INPUT));
    expect(created).toMatchObject({ name: "Ocean wonders", revision: 1, builtin: false });

    const update = renderHook(() => useSaveTemplate(created.id), { wrapper });
    const updated = await act(() =>
      update.result.current.mutateAsync({ ...INPUT, status: "ready" }),
    );
    expect(updated).toMatchObject({ status: "ready", revision: 2 });
  });

  it("maps a definition field error to its path", async () => {
    const create = renderHook(() => useSaveTemplate(undefined), { wrapper });
    const error = await rejectionOf(() =>
      create.result.current.mutateAsync({ ...INPUT, definition: { brief: " " } }),
    );
    expect(normalizeFieldErrors(fieldErrorsOf(error))).toEqual({
      "definition.brief": "Describe what the videos are about.",
    });
  });

  it("refuses to edit or delete a built-in", async () => {
    const update = renderHook(() => useSaveTemplate("kids_story"), { wrapper });
    const remove = renderHook(() => useDeleteTemplate(), { wrapper });
    const edit = await rejectionOf(() => update.result.current.mutateAsync(INPUT));
    const gone = await rejectionOf(() => remove.result.current.mutateAsync("kids_story"));
    expect(templateConflictOf(edit)?.code).toBe("template_builtin");
    expect(templateConflictOf(gone)?.code).toBe("template_builtin");
  });

  it("refuses to delete a template in use and names the automations", async () => {
    const remove = renderHook(() => useDeleteTemplate(), { wrapper });
    const error = await rejectionOf(() => remove.result.current.mutateAsync("space-facts"));
    expect(templateConflictOf(error)).toEqual({
      code: "template_in_use",
      message:
        "template is used by automations: Space facts weekly; move the automations to another pipeline and finish their runs first",
    });
  });

  it("deletes an unused template and duplicates with a new audience", async () => {
    const remove = renderHook(() => useDeleteTemplate(), { wrapper });
    const copy = renderHook(() => useDuplicateTemplate(), { wrapper });
    await act(() => remove.result.current.mutateAsync("history-five"));
    const duplicated = await act(() =>
      copy.result.current.mutateAsync({ id: "kids_story", request: { audience: "general" } }),
    );
    expect(db.state.templates.map((t) => t.id)).not.toContain("history-five");
    expect(duplicated).toMatchObject({
      name: "Kids story videos (copy)",
      audience: "general",
      status: "draft",
      origin: "duplicate",
      builtin: false,
    });
  });
});
