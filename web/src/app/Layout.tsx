import { NavLink, Outlet } from "react-router";
import { useDashboard } from "@/api/catalog";
import { type StreamState, useRunEventStream } from "@/api/eventStream";
import { Icon, type IconName } from "@/shared/ui";

interface NavItem {
  to: string;
  label: string;
  icon: IconName;
  end?: boolean;
}

const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", icon: "dashboard", end: true },
  { to: "/automations", label: "Automations", icon: "automations" },
  { to: "/runs", label: "Runs", icon: "runs" },
  { to: "/channels", label: "Channels", icon: "channels" },
  { to: "/providers", label: "Providers", icon: "providers" },
  { to: "/settings", label: "Settings", icon: "settings" },
];

const STREAM_LABELS: Record<StreamState, string> = {
  connecting: "Connecting…",
  live: "Live updates on",
  reconnecting: "Reconnecting…",
  unsupported: "Live updates unavailable",
};

function NavEntry({ item, count }: { item: NavItem; count: number }) {
  return (
    <NavLink to={item.to} end={item.end ?? false} className="nav-link" title={item.label}>
      <Icon name={item.icon} size={18} />
      <span className="nav-label">{item.label}</span>
      {count > 0 && (
        <span className="nav-count" role="img" aria-label={`${count} awaiting review`}>
          {count}
        </span>
      )}
    </NavLink>
  );
}

function Sidebar({ stream }: { stream: StreamState }) {
  const dashboard = useDashboard();
  const awaiting = dashboard.data?.runs_awaiting_review ?? 0;
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">
          <Icon name="logo" size={20} />
        </span>
        <span className="brand-name">YouTube Automator</span>
      </div>
      <nav aria-label="Main" className="nav">
        {NAV.map((item) => (
          <NavEntry key={item.to} item={item} count={item.to === "/runs" ? awaiting : 0} />
        ))}
      </nav>
      <div className={`stream stream-${stream}`}>
        <span className="stream-dot" aria-hidden="true" />
        <span className="nav-label">{STREAM_LABELS[stream]}</span>
      </div>
    </aside>
  );
}

export function Layout() {
  const stream = useRunEventStream();
  return (
    <div className="shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <Sidebar stream={stream} />
      <main id="main" className="main" tabIndex={-1}>
        <div className="content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
