import { Link } from "react-router";
import { useAutomation } from "@/api/automations";
import { isNotFound } from "@/api/errors";

export function AutomationLink({ automationId }: { automationId: string }) {
  const automation = useAutomation(automationId);
  if (isNotFound(automation.error)) {
    return <span className="muted">Automation deleted</span>;
  }
  return <Link to={`/automations/${automationId}`}>Open automation</Link>;
}
