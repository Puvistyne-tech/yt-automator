import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { usePipelines } from "@/api/catalog";
import { ApiError } from "@/api/errors";
import { keys } from "@/api/keys";
import { BUILTIN_TEMPLATES, USER_TEMPLATES } from "@/api/mocks/fixtures/templates";
import { previewUnavailableOf, templateConflictOf } from "@/api/templateErrors";
import {
  useDeleteTemplate,
  useDuplicateTemplate,
  usePreviewTemplateScript,
  useSaveTemplate,
  useTemplate,
  useTemplateEngines,
  useTemplates,
} from "@/api/templates";
import { AppProviders, createQueryClient } from "@/app/AppProviders";
import { rejectionOf, TEMPLATE_INPUT } from "../../helpers/templates";

const SEEDED_TEMPLATES = BUILTIN_TEMPLATES.length + USER_TEMPLATES.length;

function wrapper({ children }: { children: ReactNode }) {
  return <AppProviders client={createQueryClient(false)}>{children}</AppProviders>;
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

describe("previewUnavailableOf", () => {
  it("reads the server message of an unavailable preview", () => {
    const error = new ApiError(409, "preview_unavailable", "No writer.");
    expect(previewUnavailableOf(error)).toBe("No writer.");
  });

  it.each([
    new ApiError(409, "template_in_use", "other"),
    new ApiError(400, "preview_unavailable", "not a conflict status"),
    new Error("plain"),
  ])("ignores %s", (error) => {
    expect(previewUnavailableOf(error)).toBeNull();
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
    expect(list.result.current.data?.map((t) => t.builtin)).toEqual([
      ...BUILTIN_TEMPLATES.map(() => true),
      ...USER_TEMPLATES.map(() => false),
    ]);
  });

  it("does not fetch a template without an id", () => {
    const one = renderHook(() => useTemplate(undefined), { wrapper });
    expect(one.result.current.fetchStatus).toBe("idle");
  });
});

function renderMutations() {
  const client = createQueryClient(false);
  const invalidate = vi.spyOn(client, "invalidateQueries");
  const hooks = renderHook(
    () => ({
      templates: useTemplates(),
      pipelines: usePipelines(),
      create: useSaveTemplate(undefined),
      update: useSaveTemplate("history-five"),
      remove: useDeleteTemplate(),
      duplicate: useDuplicateTemplate(),
    }),
    { wrapper: ({ children }) => <AppProviders client={client}>{children}</AppProviders> },
  );
  return { client, invalidate, hooks };
}

type Hooks = ReturnType<typeof renderMutations>["hooks"]["result"]["current"];

const pipelineTypes = (hooks: Hooks) => hooks.pipelines.data?.map((p) => p.type_id) ?? [];

describe("template mutation hooks", () => {
  it.each<[string, (hooks: Hooks) => Promise<unknown>, (hooks: Hooks) => void]>([
    [
      "create",
      (h) => h.create.mutateAsync(TEMPLATE_INPUT),
      (h) => expect(pipelineTypes(h)).toContain("t_template-1"),
    ],
    [
      "update",
      (h) => h.update.mutateAsync({ ...TEMPLATE_INPUT, name: "History" }),
      (h) => expect(pipelineTypes(h)).toContain("t_history-five"),
    ],
    [
      "delete",
      (h) => h.remove.mutateAsync("history-five"),
      (h) => expect(h.templates.data?.map((t) => t.id)).not.toContain("history-five"),
    ],
    [
      "duplicate",
      (h) => h.duplicate.mutateAsync({ id: "kids_story", request: {} }),
      (h) => expect(h.templates.data).toHaveLength(SEEDED_TEMPLATES + 1),
    ],
  ])("refreshes templates and pipelines after %s", async (_name, mutate, check) => {
    const { invalidate, hooks } = renderMutations();
    await waitFor(() => expect(hooks.result.current.pipelines.data).toHaveLength(2));
    await waitFor(() => expect(hooks.result.current.templates.data).toHaveLength(SEEDED_TEMPLATES));

    await act(() => mutate(hooks.result.current));

    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.templates });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.pipelines });
    await waitFor(() => check(hooks.result.current));
  });

  it("keeps the saved template and drops a deleted one from the cache", async () => {
    const { client, hooks } = renderMutations();
    const saved = await act(() => hooks.result.current.update.mutateAsync(TEMPLATE_INPUT));
    expect(client.getQueryData(keys.template("history-five"))).toEqual(saved);

    await act(() => hooks.result.current.remove.mutateAsync("history-five"));
    expect(client.getQueryData(keys.template("history-five"))).toBeUndefined();
  });

  it("previews a sample script without refreshing anything", async () => {
    const client = createQueryClient(false);
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const preview = renderHook(() => usePreviewTemplateScript(), {
      wrapper: ({ children }) => <AppProviders client={client}>{children}</AppProviders>,
    });
    const input = { ...TEMPLATE_INPUT, language: "ta", topic: "tides" };

    const sample = await act(() => preview.result.current.mutateAsync(input));

    expect(sample).toMatchObject({ language: "ta", provider: "ollama" });
    expect(invalidate).not.toHaveBeenCalled();
  });

  it("rejects with the conflict for a built-in", async () => {
    const update = renderHook(() => useSaveTemplate("kids_story"), { wrapper });
    const edit = await rejectionOf(() => update.result.current.mutateAsync(TEMPLATE_INPUT));
    expect(templateConflictOf(edit)?.code).toBe("template_builtin");
  });
});
