import type { Run } from "@/api/types";
import { automaticEvents } from "@/features/run-detail/automaticEvents";
import { Callout, Card } from "@/shared/ui";
import "@/features/run-detail/automatic-events.css";

export function AutomaticEvents({ run }: { run: Run }) {
  const events = automaticEvents(run);
  if (events.length === 0) {
    return null;
  }
  return (
    <Card title="Automatic actions" description="What the automation's rules did on their own.">
      <ul className="list-stack automatic-events" aria-label="Automatic actions">
        {events.map((event) => (
          <li key={event.key}>
            <Callout tone={event.tone}>
              <span className="automatic-event">
                <strong>{event.title}</strong>
                <span>{event.detail}</span>
              </span>
            </Callout>
          </li>
        ))}
      </ul>
    </Card>
  );
}
