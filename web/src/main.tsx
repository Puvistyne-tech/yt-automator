import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "@/app/App";

async function enableMocks(): Promise<void> {
  if (import.meta.env.VITE_USE_MOCKS === "1") {
    const { startMockApi } = await import("@/api/mocks/browser");
    await startMockApi();
  }
}

const container = document.getElementById("root");

if (container === null) {
  throw new Error("Root element is missing from index.html");
}

void enableMocks().then(() => {
  createRoot(container).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
