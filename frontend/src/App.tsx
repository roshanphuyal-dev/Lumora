import { BrowserRouter, Routes, Route } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AppShell } from "@/components/layout/AppShell"
import { RequireAuth } from "@/components/layout/RequireAuth"
import { DashboardPage } from "@/pages/DashboardPage"
import { LoginPage } from "@/pages/LoginPage"
import { RegisterPage } from "@/pages/RegisterPage"
import { NotebookDetailPage } from "@/pages/NotebookDetailPage"
import { AuthProvider } from "@/hooks/use-auth"
import { ApiError } from "@/lib/api"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // TanStack Query's default retries any failure up to 3 times with backoff --
      // a 404/403 won't succeed on retry, so that just leaves the UI stuck on a
      // loading state for several extra seconds before showing the real error.
      retry: (failureCount, error) =>
        !(error instanceof ApiError && error.status >= 400 && error.status < 500) &&
        failureCount < 3,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route
              path="/"
              element={
                <RequireAuth>
                  <AppShell>
                    <DashboardPage />
                  </AppShell>
                </RequireAuth>
              }
            />
            <Route
              path="/notebooks/:id"
              element={
                <RequireAuth>
                  <AppShell>
                    <NotebookDetailPage />
                  </AppShell>
                </RequireAuth>
              }
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
