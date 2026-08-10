import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError } from "@/lib/api"
import { useMe } from "@/hooks/use-me"
import { useUpdateProfile } from "@/hooks/use-update-profile"

interface SettingsFormValues {
  fullName: string
}

export function SettingsPage() {
  const { data: user, isPending, isError } = useMe()
  const mutation = useUpdateProfile()
  const { register, handleSubmit, reset, formState } = useForm<SettingsFormValues>()

  useEffect(() => {
    if (user) reset({ fullName: user.full_name })
  }, [user, reset])

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-6 px-6 py-10">
      <h1 className="font-serif text-2xl font-semibold text-foreground">Settings</h1>

      {isPending ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : isError ? (
        <p className="text-sm text-destructive" role="alert">
          Couldn't load your profile.
        </p>
      ) : (
        <Card>
          <CardContent className="pt-6">
            <form
              className="flex flex-col gap-4"
              onSubmit={handleSubmit((values) => mutation.mutate(values.fullName))}
            >
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" value={user.email} disabled readOnly />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="fullName">Full name</Label>
                <Input
                  id="fullName"
                  autoComplete="name"
                  aria-invalid={!!formState.errors.fullName}
                  {...register("fullName", { required: "Full name is required" })}
                />
                {formState.errors.fullName && (
                  <p className="text-xs text-destructive">{formState.errors.fullName.message}</p>
                )}
              </div>

              {mutation.isError && (
                <p className="text-sm text-destructive" role="alert">
                  {mutation.error instanceof ApiError ? mutation.error.message : "Couldn't save changes."}
                </p>
              )}

              {mutation.isSuccess && !formState.isDirty && (
                <p className="text-sm text-success" role="status">
                  Saved.
                </p>
              )}

              <Button type="submit" disabled={mutation.isPending} className="self-start">
                {mutation.isPending ? "Saving…" : "Save changes"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
