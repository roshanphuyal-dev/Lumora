import { useQuery } from "@tanstack/react-query"
import { fetchNotebooks } from "@/lib/notebooks"

export function useNotebooks() {
  return useQuery({
    queryKey: ["notebooks"],
    queryFn: fetchNotebooks,
  })
}
