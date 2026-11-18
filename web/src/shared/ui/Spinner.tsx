export function Spinner({ size = 18, label }: { size?: number; label?: string }) {
  const style = { width: size, height: size };
  if (label === undefined) {
    return <span className="spinner" style={style} aria-hidden="true" />;
  }
  return <span className="spinner" style={style} role="status" aria-label={label} />;
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="loading-state">
      <Spinner size={22} label={label} />
      <span className="muted">{label}…</span>
    </div>
  );
}
