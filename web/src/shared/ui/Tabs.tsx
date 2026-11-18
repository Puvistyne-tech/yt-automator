import { type KeyboardEvent, type ReactNode, type RefObject, useId, useRef } from "react";

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

const tabId = (baseId: string, id: string) => `${baseId}-${id}`;

function useTabKeyboard(
  tabs: TabItem[],
  activeId: string | undefined,
  baseId: string,
  onChange: (id: string) => void,
): { listRef: RefObject<HTMLDivElement | null>; onKeyDown: (event: KeyboardEvent) => void } {
  const listRef = useRef<HTMLDivElement>(null);
  const onKeyDown = (event: KeyboardEvent) => {
    const current = tabs.findIndex((tab) => tab.id === activeId);
    const index = nextIndex(event.key, current, tabs.length);
    const target = index === null ? undefined : tabs[index];
    if (target !== undefined) {
      event.preventDefault();
      onChange(target.id);
      listRef.current?.ownerDocument.getElementById(tabId(baseId, target.id))?.focus();
    }
  };
  return { listRef, onKeyDown };
}

function TabButton({
  tab,
  baseId,
  selected,
  onSelect,
}: {
  tab: TabItem;
  baseId: string;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      id={tabId(baseId, tab.id)}
      type="button"
      role="tab"
      className="tab"
      aria-selected={selected}
      aria-controls={`${tabId(baseId, tab.id)}-panel`}
      tabIndex={selected ? 0 : -1}
      onClick={onSelect}
    >
      {tab.label}
      {tab.count !== undefined && <span className="tab-count">{tab.count}</span>}
    </button>
  );
}

export function Tabs({ label, tabs, value, onChange }: TabsProps) {
  const baseId = useId();
  const active = tabs.find((tab) => tab.id === value) ?? tabs[0];
  const keyboard = useTabKeyboard(tabs, active?.id, baseId, onChange);
  return (
    <div className="tabs">
      <div
        className="tab-list"
        role="tablist"
        aria-label={label}
        ref={keyboard.listRef}
        onKeyDown={keyboard.onKeyDown}
      >
        {tabs.map((tab) => (
          <TabButton
            key={tab.id}
            tab={tab}
            baseId={baseId}
            selected={tab.id === active?.id}
            onSelect={() => onChange(tab.id)}
          />
        ))}
      </div>
      {active && (
        <div
          className="tab-panel"
          role="tabpanel"
          id={`${tabId(baseId, active.id)}-panel`}
          aria-labelledby={tabId(baseId, active.id)}
        >
          {active.content}
        </div>
      )}
    </div>
  );
}
