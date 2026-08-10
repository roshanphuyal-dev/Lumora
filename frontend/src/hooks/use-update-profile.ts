import { useMutation, useQueryClient } from "@tanstack/react-query"
import { updateMe } from "@/lib/users"

export function useUpdateProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (fullName: string) => updateMe(fullName),
    onSuccess: (user) => {
      queryClient.setQueryData(["users", "me"], user)
    },
  })
}
