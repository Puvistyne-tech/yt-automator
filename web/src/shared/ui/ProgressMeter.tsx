import type { ReactNode } from "react";

export function meterTone(ratio: number): "success" | "warning" | "danger" {
  if (ratio >= 0.9) {
    return "danger";
  }
  return ratio >= 0.7 ? "warning" : "success";
}

interface ProgressMeterProps {
  label: string;
  value: number;
  max: number;
  detail?: ReactNode;
  tone?: "success" | "warning" | "danger" | "accent";
  hideLabel?: boolean;
}

export function ProgressMeter({
  label,
  value,
  max,
  detail,
  tone,
  hideLabel = false,
}: ProgressMeterProps) {
  const ratio = max <= 0 ? 0 : Math.min(1, Math.max(0, value / max));
  const resolved = tone ?? meterTone(ratio);
  return (
    <div className="meter">
      {!hideLabel && (
        <div className="meter-head">
          <span className="meter-label">{label}</span>
          {detail !== undefined && <span className="meter-detail">{detail}</span>}
        </div>
      )}
      <meter className="visually-hidden" aria-label={label} min={0} max={max} value={value} />
      <div className="meter-track" aria-hidden="true">
        <div className={`meter-fill meter-${resolved}`} style={{ width: `${ratio * 100}%` }} />
      </div>
    </div>
  );
}
