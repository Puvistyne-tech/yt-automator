import { useState } from "react";

export interface DraftState<T> {
  draft: T;
  setDraft: (next: T) => void;
  dirty: boolean;
  markSaved: (saved?: T) => void;
}

export function useDraftState<T>(initial: T, signature: (draft: T) => string): DraftState<T> {
  const [draft, setDraft] = useState(initial);
  const [baseline, setBaseline] = useState(() => signature(initial));
  const markSaved = (saved?: T) => {
    if (saved !== undefined) {
      setDraft(saved);
    }
    setBaseline(signature(saved ?? draft));
  };
  return { draft, setDraft, dirty: signature(draft) !== baseline, markSaved };
}
