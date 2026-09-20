import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useTerminals() {
  return useQuery({
    queryKey: ["terminals"],
    queryFn: () => api.terminals(),
  });
}

export function useVessels() {
  return useQuery({
    queryKey: ["vessels"],
    queryFn: () => api.vessels(),
  });
}
