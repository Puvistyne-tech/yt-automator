import { useEffect, useState } from "react";
import { useNavigate } from "react-router";

export function useNavigateAfterCreate(
  dirty: boolean,
  pathFor: (id: string) => string,
): (id: string) => void {
  const [createdPath, setCreatedPath] = useState<string | null>(null);
  const navigate = useNavigate();
  useEffect(() => {
    if (createdPath !== null && !dirty) {
      navigate(createdPath, { replace: true });
    }
  }, [createdPath, dirty, navigate]);
  return (id: string) => setCreatedPath(pathFor(id));
}
