import { useDeleteTemplateFlow } from "@/features/pipeline-templates/useTemplateFlows";
import { useNavigateAfterCreate } from "@/shared/hooks/useNavigateAfterCreate";

const PIPELINES_PATH = "/pipelines";

export function useEditorDelete(editor: { dirty: boolean; discard: () => void }) {
  const leave = useNavigateAfterCreate(editor.dirty, (path) => path);
  return useDeleteTemplateFlow(() => {
    editor.discard();
    leave(PIPELINES_PATH);
  });
}
