import { useEffect } from "react"
import { Check } from "lucide-react"
import { useForm } from "react-hook-form"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError } from "@/lib/api"
import { useMe } from "@/hooks/use-me"
import { useUpdateProfile } from "@/hooks/use-update-profile"
import { THEME_ACCENTS, useTheme, type ThemeAccent, type ThemeMode } from "@/hooks/use-theme"

interface SettingsFormValues {
  fullName: string
}

const MODE_OPTIONS: { value: ThemeMode; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
]

const ACCENT_SWATCH_CLASSES: Record<ThemeAccent, string> = {
  emerald: "bg-emerald-600",
  blue: "bg-blue-600",
  purple: "bg-violet-600",
  rose: "bg-rose-600",
}

const ACCENT_LABELS: Record<ThemeAccent, string> = {
  emerald: "Emerald",
  blue: "Blue",
  purple: "Purple",
  rose: "Rose",
}

function AppearanceSection() {
  const { mode, accent, setMode, setAccent } = useTheme()

  return (
    <Card>
      <CardContent className="flex flex-col gap-5 pt-6">
        <div>
          <h2 className="text-sm font-medium text-foreground">Appearance</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Applies immediately and is remembered on this browser.
          </p>
        </div>

        <div className="flex flex-col gap-2">
          <Label id="theme-mode-label">Theme</Label>
          <div role="group" aria-labelledby="theme-mode-label" className="grid grid-cols-3 gap-2">
            {MODE_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                aria-pressed={mode === option.value}
                onClick={() => setMode(option.value)}
                className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                  mode === option.value
                    ? "border-primary bg-primary/5 text-foreground"
                    : "border-border text-muted-foreground hover:bg-muted/50"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <Label id="theme-accent-label">Accent color</Label>
          <div role="group" aria-labelledby="theme-accent-label" className="flex gap-3">
            {THEME_ACCENTS.map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={accent === option}
                aria-label={ACCENT_LABELS[option]}
                title={ACCENT_LABELS[option]}
                onClick={() => setAccent(option)}
                className={`flex size-8 items-center justify-center rounded-full ${ACCENT_SWATCH_CLASSES[option]} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
                  accent === option ? "ring-2 ring-offset-2 ring-offset-background ring-foreground" : ""
                }`}
              >
                {accent === option && <Check className="size-4 text-white" aria-hidden="true" />}
              </button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
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

      <AppearanceSection />
    </div>
  )
}
