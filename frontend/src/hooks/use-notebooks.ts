import { useQuery } from "@tanstack/react-query"
import { fetchNotebooks } from "@/lib/notebooks"

export function useNotebooks(search = "") {
  return useQuery({
    queryKey: ["notebooks", { search }],
    queryFn: () => fetchNotebooks(search),
  })
}
