import { useParams } from "react-router";
import { useRun } from "@/api/runs";
import { RunDetail } from "@/features/run-detail";
import { QueryState } from "@/shared/ui";

export function RunDetailPage() {
  const { id } = useParams();
  const run = useRun(id);
  return (
    <QueryState query={run} loadingLabel="Loading run">
      {(data) => <RunDetail run={data} />}
    </QueryState>
  );
}
