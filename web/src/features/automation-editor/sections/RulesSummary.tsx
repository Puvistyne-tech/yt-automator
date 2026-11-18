export function RulesSummary({ text }: { text: string }) {
  return (
    <p className="rules-summary" aria-live="polite">
      <span className="rules-summary-label">What will happen</span>
      <span>{text}</span>
    </p>
  );
}
