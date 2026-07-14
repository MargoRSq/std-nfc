import { lazy, Suspense } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { RootLayout } from "@/components/layout/RootLayout";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { LoginPage } from "@/pages/auth/LoginPage";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "@/pages/auth/ResetPasswordPage";
import { TwoFactorSetupPage } from "@/pages/auth/TwoFactorSetupPage";
import { RequireAuth, RequireSuperAdmin } from "./guards";

const CardsListPage = lazy(() =>
  import("@/pages/admin/CardsListPage").then((m) => ({ default: m.CardsListPage })),
);
const CardEditPage = lazy(() =>
  import("@/pages/admin/CardEditPage").then((m) => ({ default: m.CardEditPage })),
);
const CardPreviewPage = lazy(() =>
  import("@/pages/admin/CardPreviewPage").then((m) => ({ default: m.CardPreviewPage })),
);
const CardAnalyticsPage = lazy(() =>
  import("@/pages/admin/CardAnalyticsPage").then((m) => ({ default: m.CardAnalyticsPage })),
);
const TemplatesPage = lazy(() =>
  import("@/pages/admin/TemplatesPage").then((m) => ({ default: m.TemplatesPage })),
);
const TemplateEditPage = lazy(() =>
  import("@/pages/admin/TemplateEditPage").then((m) => ({ default: m.TemplateEditPage })),
);
const ImportPage = lazy(() =>
  import("@/pages/admin/ImportPage").then((m) => ({ default: m.ImportPage })),
);
const AnalyticsPage = lazy(() =>
  import("@/pages/admin/AnalyticsPage").then((m) => ({ default: m.AnalyticsPage })),
);
const AdminsPage = lazy(() =>
  import("@/pages/admin/AdminsPage").then((m) => ({ default: m.AdminsPage })),
);
const AccountPage = lazy(() =>
  import("@/pages/admin/AccountPage").then((m) => ({ default: m.AccountPage })),
);

function RouteFallback() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex h-[60vh] w-full items-center justify-center"
    >
      <Loader2 className="h-6 w-6 animate-spin text-std-muted-fg" />
      <span className="sr-only">Загрузка…</span>
    </div>
  );
}

const lazyRoute = (element: React.ReactNode) => (
  <Suspense fallback={<RouteFallback />}>{element}</Suspense>
);

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      { path: "/", element: <Navigate to="/admin/cards" replace /> },
      {
        element: <AuthLayout />,
        children: [
          { path: "/login", element: <LoginPage /> },
          { path: "/forgot-password", element: <ForgotPasswordPage /> },
          { path: "/reset-password", element: <ResetPasswordPage /> },
        ],
      },
      {
        element: (
          <RequireAuth>
            <AdminLayout />
          </RequireAuth>
        ),
        children: [
          { path: "/admin", element: <Navigate to="/admin/cards" replace /> },
          { path: "/admin/cards", element: lazyRoute(<CardsListPage />) },
          { path: "/admin/cards/new", element: lazyRoute(<CardEditPage mode="create" />) },
          { path: "/admin/cards/:id", element: lazyRoute(<CardPreviewPage />) },
          { path: "/admin/cards/:id/edit", element: lazyRoute(<CardEditPage mode="edit" />) },
          { path: "/admin/cards/:id/analytics", element: lazyRoute(<CardAnalyticsPage />) },
          { path: "/admin/templates", element: lazyRoute(<TemplatesPage />) },
          { path: "/admin/templates/:id/edit", element: lazyRoute(<TemplateEditPage />) },
          { path: "/admin/import", element: lazyRoute(<ImportPage />) },
          { path: "/admin/analytics", element: lazyRoute(<AnalyticsPage />) },
          { path: "/admin/account", element: lazyRoute(<AccountPage />) },
          { path: "/admin/2fa-setup", element: <TwoFactorSetupPage /> },
          {
            path: "/admin/admins",
            element: (
              <RequireSuperAdmin>
                {lazyRoute(<AdminsPage />)}
              </RequireSuperAdmin>
            ),
          },
        ],
      },
    ],
  },
]);
