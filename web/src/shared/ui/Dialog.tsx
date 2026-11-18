import { type ReactNode, type RefObject, useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";
import { IconButton } from "@/shared/ui/Button";

const FOCUSABLE =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

interface DialogProps {
  open: boolean;
  title: string;
  description?: ReactNode;
  onClose: () => void;
  footer?: ReactNode;
  size?: "sm" | "md" | "lg";
  children?: ReactNode;
}

function focusables(panel: HTMLElement | null): HTMLElement[] {
  return panel ? Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)) : [];
}

function trapTab(event: KeyboardEvent, panel: HTMLElement | null) {
  const items = focusables(panel);
  const first = items[0];
  const last = items[items.length - 1];
  if (first === undefined || last === undefined) {
    return;
  }
  const active = document.activeElement;
  if (event.shiftKey && active === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
}

function useInitialFocus(open: boolean, panel: RefObject<HTMLDivElement | null>) {
  useEffect(() => {
    if (!open) {
      return;
    }
    const previous = document.activeElement as HTMLElement | null;
    const body = panel.current?.querySelector<HTMLElement>(".dialog-body");
    const target = focusables(body ?? null)[0] ?? focusables(panel.current)[0];
    target?.focus();
    return () => previous?.focus();
  }, [open, panel]);
}

function useDialogKeys(
  open: boolean,
  panel: RefObject<HTMLDivElement | null>,
  onClose: () => void,
) {
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    if (!open) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        close.current();
      } else if (event.key === "Tab") {
        trapTab(event, panel.current);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, panel]);
}

export function Dialog({
  open,
  title,
  description,
  onClose,
  footer,
  size = "md",
  children,
}: DialogProps) {
  const titleId = useId();
  const panel = useRef<HTMLDivElement>(null);
  useInitialFocus(open, panel);
  useDialogKeys(open, panel, onClose);
  if (!open) {
    return null;
  }
  return createPortal(
    <div className="dialog-backdrop">
      <div
        ref={panel}
        className={`dialog dialog-${size}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <header className="dialog-header">
          <div>
            <h2 id={titleId}>{title}</h2>
            {description !== undefined && <p className="muted">{description}</p>}
          </div>
          <IconButton icon="x" label="Close" onClick={onClose} />
        </header>
        {children !== undefined && <div className="dialog-body">{children}</div>}
        {footer !== undefined && <footer className="dialog-footer">{footer}</footer>}
      </div>
    </div>,
    document.body,
  );
}
