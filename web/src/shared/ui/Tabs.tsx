import { type KeyboardEvent, type ReactNode, useId, useRef } from "react";

export interface TabItem {
  id: string;
  label: string;
  count?: number | undefined;
  content: ReactNode;
}

interface TabsProps {
  label: string;
  tabs: TabItem[];
  value: string;
  onChange: (id: string) => void;
}

function nextIndex(key: string, current: number, total: number): number | null {
  switch (key) {
    case "ArrowRight":
      return (current + 1) % total;
    case "ArrowLeft":
      return (current - 1 + total) % total;
    case "Home":
      return 0;
    case "End":
      return total - 1;
    default:
      return null;
  }
}

export function Tabs({ label, tabs, value, onChange }: TabsProps) {
  const baseId = useId();
  const listRef = useRef<HTMLDivElement>(null);
  const active = tabs.find((tab) => tab.id === value) ?? tabs[0];
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const index = nextIndex(
      event.key,
      tabs.findIndex((tab) => tab.id === active?.id),
      tabs.length,
    );
    const target = index === null ? undefined : tabs[index];
    if (target !== undefined) {
      event.preventDefault();
      onChange(target.id);
      listRef.current?.ownerDocument.getElementById(`${baseId}-${target.id}`)?.focus();
    }
  };
  return (
    <div className="tabs">
      <div
        className="tab-list"
        role="tablist"
        aria-label={label}
        ref={listRef}
        onKeyDown={onKeyDown}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            id={`${baseId}-${tab.id}`}
            type="button"
            role="tab"
            className="tab"
            aria-selected={tab.id === active?.id}
            aria-controls={`${baseId}-${tab.id}-panel`}
            tabIndex={tab.id === active?.id ? 0 : -1}
            onClick={() => onChange(tab.id)}
          >
            {tab.label}
            {tab.count !== undefined && <span className="tab-count">{tab.count}</span>}
          </button>
        ))}
      </div>
      {active && (
        <div
          className="tab-panel"
          role="tabpanel"
          id={`${baseId}-${active.id}-panel`}
          aria-labelledby={`${baseId}-${active.id}`}
        >
          {active.content}
        </div>
      )}
    </div>
  );
}
