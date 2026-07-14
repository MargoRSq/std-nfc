import { Navigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";

interface GuardProps {
  children: React.ReactNode;
}

export function RequireAuth({ children }: GuardProps) {
  const accessToken = useAuthStore((s) => s.accessToken);
  if (!accessToken) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function RequireSuperAdmin({ children }: GuardProps) {
  const user = useAuthStore((s) => s.user);
  if (user?.role !== "super_admin") return <Navigate to="/admin/cards" replace />;
  return <>{children}</>;
}
