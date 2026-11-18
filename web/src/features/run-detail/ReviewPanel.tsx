import { useState } from "react";
import { errorMessage } from "@/api/errors";
import { useReviewRun } from "@/api/runs";
import type { Run } from "@/api/types";
import { formatScore } from "@/shared/format/numbers";
import { Button, Card, FormField, Textarea, useToast } from "@/shared/ui";

type Decision = "approved" | "rejected";

export function ReviewPanel({ run }: { run: Run }) {
  const [notes, setNotes] = useState("");
  const review = useReviewRun();
  const toast = useToast();
  const decide = (decision: Decision) =>
    review
      .mutateAsync({
        id: run.id,
        vars: notes.trim() === "" ? { decision } : { decision, notes: notes.trim() },
      })
      .then(
        () =>
          toast.success(
            decision === "approved" ? "Run approved. You can publish it now." : "Run rejected.",
          ),
        (error: unknown) => toast.error(errorMessage(error)),
      );
  const pendingDecision = review.isPending ? review.variables?.vars.decision : undefined;
  return (
    <Card
      className="review-panel"
      title="Review this run"
      description={`Watch the videos below, then approve or reject. Score ${formatScore(run.score)}.`}
    >
      <div className="stack">
        <FormField label="Review notes" hint="Optional. Saved with your decision.">
          <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </FormField>
        <div className="row">
          <Button
            variant="primary"
            icon="check"
            loading={pendingDecision === "approved"}
            disabled={review.isPending}
            onClick={() => decide("approved")}
          >
            Approve
          </Button>
          <Button
            variant="danger"
            icon="x"
            loading={pendingDecision === "rejected"}
            disabled={review.isPending}
            onClick={() => decide("rejected")}
          >
            Reject
          </Button>
        </div>
      </div>
    </Card>
  );
}
