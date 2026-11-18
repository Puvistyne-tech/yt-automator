import { useState } from "react";
import { useReviewRun } from "@/api/runs";
import type { Run } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import {
  type Decision,
  reviewMessage,
  reviewPayload,
  reviewRuleLabel,
} from "@/features/run-detail/model";
import { formatScore } from "@/shared/format/numbers";
import { Button, Card, FormField, Textarea } from "@/shared/ui";

function DecisionButtons({
  pending,
  busy,
  onDecide,
}: {
  pending: Decision | undefined;
  busy: boolean;
  onDecide: (decision: Decision) => void;
}) {
  return (
    <div className="row">
      <Button
        variant="primary"
        icon="check"
        loading={pending === "approved"}
        disabled={busy}
        onClick={() => onDecide("approved")}
      >
        Approve
      </Button>
      <Button
        variant="danger"
        icon="x"
        loading={pending === "rejected"}
        disabled={busy}
        onClick={() => onDecide("rejected")}
      >
        Reject
      </Button>
    </div>
  );
}

export function ReviewPanel({ run }: { run: Run }) {
  const [notes, setNotes] = useState("");
  const review = useReviewRun();
  const notifier = useMutationNotifier();
  const decide = (decision: Decision) =>
    notifier.track(review.mutateAsync({ id: run.id, vars: reviewPayload(decision, notes) }), {
      success: reviewMessage(decision),
    });
  const pending = review.isPending ? review.variables?.vars.decision : undefined;
  return (
    <Card
      className="review-panel"
      title="Review this run"
      description={`Watch the videos below, then approve or reject. Score ${formatScore(run.score)} · ${reviewRuleLabel(run.review_policy)}.`}
    >
      <div className="stack">
        <FormField label="Review notes" hint="Optional. Saved with your decision.">
          <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </FormField>
        <DecisionButtons pending={pending} busy={review.isPending} onDecide={decide} />
      </div>
    </Card>
  );
}
