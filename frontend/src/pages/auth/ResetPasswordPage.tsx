import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { authApi } from "@/lib/api/auth";

const schema = z
  .object({
    new_password: z
      .string()
      .min(8, "Минимум 8 символов")
      .regex(/[a-zA-Z]/, "Должна быть хотя бы одна буква")
      .regex(/\d/, "Должна быть хотя бы одна цифра"),
    confirm_password: z.string().min(1, "Подтвердите пароль"),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: "Пароли не совпадают",
    path: ["confirm_password"],
  });

type FormData = z.infer<typeof schema>;

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { new_password: "", confirm_password: "" },
  });

  const onSubmit = async (data: FormData) => {
    if (!token) {
      setError("Токен сброса отсутствует. Запросите новую ссылку.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      await authApi.passwordResetConfirm(token, data.new_password);
      toast.success("Пароль успешно изменён");
      navigate("/login");
    } catch (err: unknown) {
      const e = err as { response?: { status?: number; data?: { detail?: string } } };
      const status = e?.response?.status;
      if (status === 400 || status === 404) {
        setError("Ссылка недействительна или истекла. Запросите новую.");
      } else {
        setError(e?.response?.data?.detail ?? "Ошибка сброса пароля. Попробуйте позже.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Новый пароль</CardTitle>
        <CardDescription>Придумайте новый пароль для вашего аккаунта</CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            {error && (
              <p className="text-sm text-destructive rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2">
                {error}
              </p>
            )}
            <FormField
              control={form.control}
              name="new_password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Новый пароль</FormLabel>
                  <FormControl>
                    <Input {...field} type="password" placeholder="••••••••" autoFocus autoComplete="new-password" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="confirm_password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Подтвердите пароль</FormLabel>
                  <FormControl>
                    <Input {...field} type="password" placeholder="••••••••" autoComplete="new-password" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" disabled={isLoading} className="w-full">
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Сохранить пароль
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
