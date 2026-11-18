import { createContext, useContext } from "react";

export type ExternalNavigate = (url: string) => void;

const assignLocation: ExternalNavigate = (url) => window.location.assign(url);

export const ExternalNavigationContext = createContext<ExternalNavigate>(assignLocation);

export function useExternalNavigate(): ExternalNavigate {
  return useContext(ExternalNavigationContext);
}
