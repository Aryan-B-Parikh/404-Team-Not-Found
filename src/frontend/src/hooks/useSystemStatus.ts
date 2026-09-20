import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useSystemHealth() {
  return useQuery({
    queryKey: ["systemHealth"],
    queryFn: () => api.health(),
    refetchInterval: 30_000,
  });
}
