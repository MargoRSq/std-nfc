import { type ComponentType } from "react";
import { Outlet, NavLink, useNavigate, useLocation, Link } from "react-router-dom";
import { User, LayoutTemplate, Upload } from "lucide-react";
import {
  PlusIcon,
  GridIcon,
  ChartIcon,
  UsersGroupIcon,
  UserCircleIcon,
  LogoutIcon,
} from "@/components/icons/NavIcons";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuthStore } from "@/stores/authStore";
import { authApi } from "@/lib/api/auth";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

type IconType = ComponentType<{ className?: string }>;

interface NavItem {
  to: string;
  label: string;
  icon: IconType;
  superAdminOnly?: boolean;
  exact?: boolean;
}

const navItems: NavItem[] = [
  { to: "/admin/cards/new", label: "Создать", icon: PlusIcon, exact: true },
  { to: "/admin/cards", label: "Карточки", icon: GridIcon },
  { to: "/admin/analytics", label: "Аналитика", icon: ChartIcon },
  { to: "/admin/admins", label: "Администраторы", icon: UsersGroupIcon, superAdminOnly: true },
];

const mobileTabItems: NavItem[] = [
  { to: "/admin/cards", label: "Карточки", icon: GridIcon },
  { to: "/admin/cards/new", label: "Создать", icon: PlusIcon, exact: true },
  { to: "/admin/analytics", label: "Аналитика", icon: ChartIcon },
];

function isItemActive(pathname: string, item: NavItem) {
  if (item.exact) return pathname === item.to;
  if (item.to === "/admin/cards") {
    return pathname.startsWith("/admin/cards") && pathname !== "/admin/cards/new";
  }
  return pathname.startsWith(item.to);
}

function NavPill({
  to,
  label,
  icon: Icon,
  active,
  onClick,
}: {
  to: string;
  label: string;
  icon: IconType;
  active: boolean;
  onClick?: () => void;
}) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-base transition-colors whitespace-nowrap",
        active
          ? "bg-std-surface-2 text-black"
          : "text-std-muted-fg hover:bg-std-surface-2",
      )}
    >
      <Icon className="w-[18px] h-[18px] flex-shrink-0" />
      {label}
    </NavLink>
  );
}

function MobileTab({
  to,
  label,
  icon: Icon,
  active,
}: {
  to: string;
  label: string;
  icon: IconType;
  active: boolean;
}) {
  return (
    <NavLink
      to={to}
      className={cn(
        "flex flex-col items-center justify-center gap-1 flex-1 h-full text-caption transition-colors",
        active ? "text-std-primary" : "text-std-muted-fg",
      )}
    >
      <Icon className="w-5 h-5" />
      <span className="leading-none">{label}</span>
    </NavLink>
  );
}

export function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const refreshToken = useAuthStore((s) => s.refreshToken);

  const handleLogout = async () => {
    try {
      if (refreshToken) await authApi.logout(refreshToken);
    } catch {
      // ignore
    }
    logout();
    navigate("/login");
    toast.success("Вы вышли из системы");
  };

  const localPart = user?.email?.split("@")[0] ?? "";
  const nameParts = localPart.split(/[._-]/).filter(Boolean);
  const displayName = nameParts.length > 0
    ? nameParts.map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join(" ")
    : "Аккаунт";
  const visibleNav = navItems.filter(
    (item) => !item.superAdminOnly || user?.role === "super_admin",
  );
  const isSuperAdmin = user?.role === "super_admin";

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 bg-white border-b border-std-border">
        <div className="h-16 flex items-center gap-3 md:gap-6 px-4 md:px-[60px]">
          <Link
            to="/admin/cards"
            className="flex-shrink-0 inline-flex items-center"
            aria-label="СТД"
          >
            <img src="/std-logo-full-dark.png" alt="СТД" className="h-8 w-auto" />
          </Link>

          <nav className="hidden md:flex items-center gap-2 flex-1">
            {visibleNav.map((item) => (
              <NavPill
                key={item.to}
                to={item.to}
                label={item.label}
                icon={item.icon}
                active={isItemActive(location.pathname, item)}
              />
            ))}
          </nav>

          <div className="flex items-center gap-1 flex-shrink-0 ml-auto">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="flex items-center gap-2 rounded-2xl px-2 py-1 hover:bg-std-surface-2 transition-colors focus:outline-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-std-primary/40"
                  aria-label="Меню аккаунта"
                  title="Аккаунт"
                >
                  <Avatar className="h-9 w-9 flex-shrink-0 rounded-full">
                    <AvatarFallback className="bg-std-border text-std-muted-fg rounded-full">
                      <User className="h-5 w-5" />
                    </AvatarFallback>
                  </Avatar>
                  <span className="hidden md:block text-sm font-medium text-black truncate max-w-[180px]">
                    {displayName}
                  </span>
                  <LogoutIcon className="h-4 w-4 text-muted-foreground" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                {user?.email && (
                  <DropdownMenuLabel className="truncate">{user.email}</DropdownMenuLabel>
                )}
                {user?.email && <DropdownMenuSeparator />}
                <DropdownMenuItem onClick={() => navigate("/admin/account")}>
                  <UserCircleIcon className="mr-2 h-4 w-4" />
                  Аккаунт
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate("/admin/templates")}>
                  <LayoutTemplate className="mr-2 h-4 w-4" />
                  Шаблоны
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate("/admin/import")}>
                  <Upload className="mr-2 h-4 w-4" />
                  Импорт
                </DropdownMenuItem>
                {isSuperAdmin && (
                  <DropdownMenuItem onClick={() => navigate("/admin/admins")}>
                    <UsersGroupIcon className="mr-2 h-4 w-4" />
                    Администраторы
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout}>
                  <LogoutIcon className="mr-2 h-4 w-4" />
                  Выйти
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-6 py-4 md:py-8 md:pb-8" style={{ paddingBottom: "calc(76px + env(safe-area-inset-bottom))" }}>
        <Outlet />
      </main>

      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-std-border flex items-stretch"
        style={{
          height: "calc(60px + env(safe-area-inset-bottom))",
          paddingBottom: "env(safe-area-inset-bottom)",
        }}
        aria-label="Нижняя навигация"
      >
        {mobileTabItems.map((item) => (
          <MobileTab
            key={item.to}
            to={item.to}
            label={item.label}
            icon={item.icon}
            active={isItemActive(location.pathname, item)}
          />
        ))}
      </nav>

    </div>
  );
}
