import { useEffect, useState } from "react";
import { useNavigate } from "react-router";

export function useNavigateAfterCreate(dirty: boolean): (id: string) => void {
  const [createdId, setCreatedId] = useState<string | null>(null);
  const navigate = useNavigate();
  useEffect(() => {
    if (createdId !== null && !dirty) {
      navigate(`/automations/${createdId}`, { replace: true });
    }
  }, [createdId, dirty, navigate]);
  return setCreatedId;
}
