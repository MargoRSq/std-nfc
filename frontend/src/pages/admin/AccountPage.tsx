import { ArrowLeft, Shield } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/stores/authStore";

export function AccountPage() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();

  return (
    <div className="max-w-lg space-y-6">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="h-10 w-10 rounded-full border border-std-border bg-white"
          onClick={() => navigate("/admin/cards")}
          aria-label="Назад"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-2xl font-bold">Аккаунт</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Информация</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Email</span>
            <span className="font-medium">{user?.email}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Роль</span>
            <span className="font-medium">
              {user?.role === "super_admin" ? "Суперадмин" : "Администратор"}
            </span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Двухфакторная аутентификация
          </CardTitle>
          <CardDescription>Дополнительная защита аккаунта</CardDescription>
        </CardHeader>
        <CardContent>
          <Link to="/admin/2fa-setup">
            <Button variant="outline">Настроить 2FA</Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
