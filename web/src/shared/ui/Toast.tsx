import { createContext, type ReactNode, useCallback, useContext, useMemo, useState } from "react";
import { IconButton } from "@/shared/ui/Button";
import { Icon, type IconName } from "@/shared/ui/Icon";

type ToastTone = "success" | "error" | "info";

interface ToastItem {
  id: number;
  tone: ToastTone;
  message: string;
}

interface ToastApi {
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const ICONS: Record<ToastTone, IconName> = { success: "check", error: "alert", info: "info" };
const DURATION_MS = 5000;

let nextId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const dismiss = useCallback((id: number) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);
  const push = useCallback(
    (tone: ToastTone, message: string) => {
      nextId += 1;
      const id = nextId;
      setItems((current) => [...current.slice(-3), { id, tone, message }]);
      setTimeout(() => dismiss(id), DURATION_MS);
    },
    [dismiss],
  );
  const toastApi = useMemo<ToastApi>(
    () => ({
      success: (message) => push("success", message),
      error: (message) => push("error", message),
      info: (message) => push("info", message),
    }),
    [push],
  );
  return (
    <ToastContext.Provider value={toastApi}>
      {children}
      <section className="toast-region" aria-label="Notifications" aria-live="polite">
        {items.map((item) => (
          <div key={item.id} className={`toast toast-${item.tone}`} role="status">
            <span className="toast-icon">
              <Icon name={ICONS[item.tone]} />
            </span>
            <span className="toast-message">{item.message}</span>
            <IconButton icon="x" label="Dismiss notification" onClick={() => dismiss(item.id)} />
          </div>
        ))}
      </section>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const toast = useContext(ToastContext);
  if (toast === null) {
    throw new Error("useToast must be used inside ToastProvider");
  }
  return toast;
}
