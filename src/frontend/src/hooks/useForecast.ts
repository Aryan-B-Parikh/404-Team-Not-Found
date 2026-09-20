import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useForecast(zoneCode: string = "Z-PORT") {
  return useQuery({
    queryKey: ["forecast", zoneCode],
    queryFn: () => api.forecast(zoneCode),
    enabled: Boolean(zoneCode),
  });
}
