import { useForm } from "react-hook-form"
import { useMutation } from "@tanstack/react-query"
import { Link, useNavigate } from "react-router-dom"
import { AuthLayout } from "@/components/layout/AuthLayout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { ApiError } from "@/lib/api"
import { login, loginWithGoogle, register as registerAccount } from "@/lib/auth"
import { useAuth } from "@/hooks/use-auth"
import { GoogleLoginButton } from "@/components/auth/GoogleLoginButton"

interface RegisterFormValues {
  fullName: string
  email: string
  password: string
}

export function RegisterPage() {
  const navigate = useNavigate()
  const { signIn } = useAuth()
  const {
    register: registerField,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>()

  const mutation = useMutation({
    mutationFn: async (values: RegisterFormValues) => {
      await registerAccount(values.email, values.password, values.fullName)
      // register only creates the account (docs/API.md); log in immediately after
      // so the student lands straight in the product instead of a second form.
      return login(values.email, values.password)
    },
    onSuccess: (tokens) => {
      signIn(tokens.access_token, tokens.refresh_token)
      navigate("/", { replace: true })
    },
  })

  const googleMutation = useMutation({
    mutationFn: (idToken: string) => loginWithGoogle(idToken),
    onSuccess: (tokens) => {
      signIn(tokens.access_token, tokens.refresh_token)
      navigate("/", { replace: true })
    },
  })

  return (
    <AuthLayout>
      <form
        className="flex flex-col gap-4"
        onSubmit={handleSubmit((values) => mutation.mutate(values))}
        noValidate
      >
        <div className="flex flex-col gap-1">
          <h1 className="text-lg font-medium text-foreground">Create your account</h1>
          <p className="text-sm text-muted-foreground">Start turning your material into study resources.</p>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="fullName">Full name</Label>
          <Input
            id="fullName"
            autoComplete="name"
            aria-invalid={!!errors.fullName}
            {...registerField("fullName", { required: "Full name is required" })}
          />
          {errors.fullName && <p className="text-xs text-destructive">{errors.fullName.message}</p>}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            aria-invalid={!!errors.email}
            {...registerField("email", { required: "Email is required" })}
          />
          {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            aria-invalid={!!errors.password}
            {...registerField("password", {
              required: "Password is required",
              minLength: { value: 8, message: "At least 8 characters" },
            })}
          />
          {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
        </div>

        {(mutation.isError || googleMutation.isError) && (
          <p className="text-sm text-destructive" role="alert">
            {mutation.error instanceof ApiError
              ? mutation.error.message
              : googleMutation.error instanceof ApiError
                ? googleMutation.error.message
                : "Something went wrong."}
          </p>
        )}

        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Creating account…" : "Create account"}
        </Button>

        <div className="flex items-center gap-3">
          <Separator className="flex-1" />
          <span className="text-xs text-muted-foreground">or</span>
          <Separator className="flex-1" />
        </div>

        <GoogleLoginButton onIdToken={(idToken) => googleMutation.mutate(idToken)} />

        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Log in
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
