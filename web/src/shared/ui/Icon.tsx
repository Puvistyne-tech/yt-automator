const PATHS = {
  dashboard: "M3 3h8v8H3z M13 3h8v5h-8z M13 10h8v11h-8z M3 13h8v8H3z",
  automations: "M13 2 4 14h7l-1 8 9-12h-7z",
  pipelines: "M12 2 2 7l10 5 10-5z M2 12l10 5 10-5 M2 17l10 5 10-5",
  runs: "M22 12h-4l-3 9L9 3l-3 9H2",
  channels: "M2 7h20v13H2z M17 2l-5 5-5-5",
  providers:
    "M6 6h12v12H6z M9 9h6v6H9z M9 2v4 M15 2v4 M9 18v4 M15 18v4 M2 9h4 M2 15h4 M18 9h4 M18 15h4",
  settings: "M4 21v-7 M4 10V3 M12 21v-9 M12 8V3 M20 21v-5 M20 12V3 M1 14h6 M9 8h6 M17 16h6",
  plus: "M12 5v14 M5 12h14",
  edit: "M16.5 3.5l4 4L8 20H4v-4z",
  copy: "M8 8h12v12H8z M4 16V4h12",
  trash: "M3 6h18 M8 6V4h8v2 M6 6l1 14h10l1-14",
  play: "M7 4l13 8-13 8z",
  up: "M18 15l-6-6-6 6",
  down: "M6 9l6 6 6-6",
  right: "M9 6l6 6-6 6",
  left: "M19 12H5 M12 19l-7-7 7-7",
  check: "M20 6 9 17l-5-5",
  x: "M18 6 6 18 M6 6l12 12",
  external: "M14 4h6v6 M20 4l-9 9 M18 14v6H4V6h6",
  refresh: "M21 12a9 9 0 1 1-3-6.7 M21 3v6h-6",
  spark: "M12 3l2 7 7 2-7 2-2 7-2-7-7-2 7-2z",
  alert: "M12 3 2 21h20z M12 10v5 M12 18h.01",
  info: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z M12 16v-5 M12 8h.01",
  link: "M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1 M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1",
  key: "M7.5 21a4.5 4.5 0 1 1 3.2-7.7L19 5l2 2-2 2 2 2-2 2-2-2-3.8 3.8A4.5 4.5 0 0 1 7.5 21z",
  clock: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z M12 6v6l4 2",
  stop: "M6 6h12v12H6z",
  inbox: "M22 12h-6l-2 3h-4l-2-3H2 M5.5 5h13L22 12v7H2v-7z",
  film: "M3 3h18v18H3z M7 3v18 M17 3v18 M3 8h4 M3 16h4 M17 8h4 M17 16h4",
  file: "M14 2H6v20h12V8z M14 2v6h6",
  upload: "M12 16V4 M7 9l5-5 5 5 M4 20h16",
  logo: "M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v11a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 17.5z M10 9l5 3-5 3z",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 16 }: { name: IconName; size?: number }) {
  return (
    <svg
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
