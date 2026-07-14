import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { authApi } from "@/lib/api/auth";

const schema = z.object({
  email: z.string().email("Некорректный email"),
});

type FormData = z.infer<typeof schema>;

export function ForgotPasswordPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { email: "" },
  });

  const onSubmit = async (data: FormData) => {
    setIsLoading(true);
    try {
      await authApi.passwordResetRequest(data.email);
      setSent(true);
      toast.success("Инструкция отправлена на email");
    } catch {
      toast.error("Ошибка отправки. Попробуйте позже.");
    } finally {
      setIsLoading(false);
    }
  };

  if (sent) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Письмо отправлено</CardTitle>
          <CardDescription>
            Проверьте почту и следуйте инструкции для сброса пароля.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Link to="/login">
            <Button variant="outline" className="w-full">
              Вернуться к входу
            </Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Сброс пароля</CardTitle>
        <CardDescription>Введите email для получения инструкций по сбросу пароля</CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input {...field} type="email" placeholder="admin@example.com" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" disabled={isLoading} className="w-full">
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Отправить
            </Button>
            <Link to="/login" className="block text-center text-sm text-muted-foreground hover:underline">
              Вернуться к входу
            </Link>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
