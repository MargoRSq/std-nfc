import { Outlet } from "react-router-dom";
import { HelmetProvider, Helmet } from "react-helmet-async";
import { ErrorBoundary } from "react-error-boundary";
import { Toaster } from "sonner";

function ErrorFallback({ error }: { error: Error }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-8">
      <h2 className="text-xl font-semibold text-destructive">Что-то пошло не так</h2>
      <p className="mt-2 text-sm text-muted-foreground">{error.message}</p>
      <button
        className="mt-4 text-sm text-primary underline"
        onClick={() => window.location.reload()}
      >
        Перезагрузить страницу
      </button>
    </div>
  );
}

export function RootLayout() {
  return (
    <HelmetProvider>
      <Helmet>
        <meta name="robots" content="noindex" />
      </Helmet>
      <ErrorBoundary FallbackComponent={ErrorFallback}>
        <Outlet />
        <Toaster position="top-right" richColors />
      </ErrorBoundary>
    </HelmetProvider>
  );
}
