import { useForm } from "react-hook-form"
import { useMutation } from "@tanstack/react-query"
import { Link, useNavigate } from "react-router-dom"
import { AuthLayout } from "@/components/layout/AuthLayout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { ApiError } from "@/lib/api"
import { login, loginWithGoogle } from "@/lib/auth"
import { useAuth } from "@/hooks/use-auth"
import { GoogleLoginButton } from "@/components/auth/GoogleLoginButton"

interface LoginFormValues {
  email: string
  password: string
}

export function LoginPage() {
  const navigate = useNavigate()
  const { signIn } = useAuth()
  const {
    register: registerField,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>()

  const mutation = useMutation({
    mutationFn: (values: LoginFormValues) => login(values.email, values.password),
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
          <h1 className="text-lg font-medium text-foreground">Log in</h1>
          <p className="text-sm text-muted-foreground">Welcome back.</p>
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
            autoComplete="current-password"
            aria-invalid={!!errors.password}
            {...registerField("password", { required: "Password is required" })}
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
          {mutation.isPending ? "Logging in…" : "Log in"}
        </Button>

        <div className="flex items-center gap-3">
          <Separator className="flex-1" />
          <span className="text-xs text-muted-foreground">or</span>
          <Separator className="flex-1" />
        </div>

        <GoogleLoginButton onIdToken={(idToken) => googleMutation.mutate(idToken)} />

        <p className="text-center text-sm text-muted-foreground">
          Don't have an account?{" "}
          <Link to="/register" className="font-medium text-primary hover:underline">
            Sign up
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
