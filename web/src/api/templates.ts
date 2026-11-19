import { type QueryClient, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { keys } from "@/api/keys";
import type {
  DuplicateTemplateRequest,
  EngineSummary,
  SampleScript,
  TemplateInput,
  TemplatePreviewInput,
  TemplateSummary,
} from "@/api/types";

const path = (id: string) => `/templates/${encodeURIComponent(id)}`;

function refreshTemplates(client: QueryClient): Promise<unknown> {
  return Promise.all(
    [keys.templates, keys.pipelines].map((queryKey) => client.invalidateQueries({ queryKey })),
  );
}

export function useTemplateEngines() {
  return useQuery({
    queryKey: keys.templateEngines,
    queryFn: () => api.get<EngineSummary[]>("/template-engines"),
    staleTime: 5 * 60 * 1000,
  });
}

export function useTemplates() {
  return useQuery({
    queryKey: keys.templates,
    queryFn: () => api.get<TemplateSummary[]>("/templates"),
  });
}

export function useTemplate(id: string | undefined) {
  return useQuery({
    queryKey: keys.template(id ?? ""),
    queryFn: () => api.get<TemplateSummary>(path(id ?? "")),
    enabled: id !== undefined,
  });
}

export function useSaveTemplate(id: string | undefined) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: TemplateInput) =>
      id === undefined
        ? api.post<TemplateSummary>("/templates", input)
        : api.put<TemplateSummary>(path(id), input),
    onSuccess: (saved) => {
      client.setQueryData(keys.template(saved.id), saved);
      return refreshTemplates(client);
    },
  });
}

export function useDeleteTemplate() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(path(id)),
    onSuccess: (_data, id) => {
      client.removeQueries({ queryKey: keys.template(id), exact: true });
      return refreshTemplates(client);
    },
  });
}

export function useDuplicateTemplate() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, request }: { id: string; request: DuplicateTemplateRequest }) =>
      api.post<TemplateSummary>(`${path(id)}/duplicate`, request),
    onSuccess: () => refreshTemplates(client),
  });
}

export function usePreviewTemplateScript() {
  return useMutation({
    mutationFn: (input: TemplatePreviewInput) =>
      api.post<SampleScript>("/templates/preview-script", input),
  });
}
