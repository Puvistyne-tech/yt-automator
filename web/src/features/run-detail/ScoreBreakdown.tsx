import type { Run } from "@/api/types";
import { reviewRuleLabel, scoreTone, weightedScore } from "@/features/run-detail/model";
import { formatScore } from "@/shared/format/numbers";
import { EmptyState, ProgressMeter } from "@/shared/ui";

export function ScoreBreakdown({ run }: { run: Run }) {
  if (run.score_details.length === 0) {
    return (
      <EmptyState
        icon="info"
        title="Not scored yet"
        description="The run is scored after its last stage finishes."
      />
    );
  }
  const overall = run.score ?? weightedScore(run.score_details);
  return (
    <div className="stack">
      <div className="score-overall">
        <span className="score-value">{formatScore(overall)}</span>
        <span className="muted">overall score out of 100</span>
        <span className="score-rule">{reviewRuleLabel(run.review_policy)}</span>
      </div>
      <ul className="list-stack">
        {run.score_details.map((item) => (
          <li key={item.id} className="score-item">
            <ProgressMeter
              label={item.title}
              value={item.score}
              max={100}
              tone={scoreTone(item.score)}
              detail={`${formatScore(item.score)} · weight ${Math.round(item.weight * 100)}%`}
            />
            {item.detail && <p className="subtle">{item.detail}</p>}
          </li>
        ))}
      </ul>
    </div>
  );
}
