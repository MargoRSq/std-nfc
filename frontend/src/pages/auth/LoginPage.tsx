import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate } from "react-router-dom";
import { Info, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Checkbox } from "@/components/ui/checkbox";
import { AuthShell } from "@/components/auth/AuthShell";
import { authApi } from "@/lib/api/auth";
import { useAuthStore, setRememberMe } from "@/stores/authStore";

const loginSchema = z.object({
  email: z.string().email("Некорректный email"),
  password: z.string().min(1, "Введите пароль"),
});

const totpSchema = z.object({
  code: z.string().length(6, "Код должен быть 6 цифр").regex(/^\d+$/, "Только цифры"),
});

const recoverySchema = z.object({
  recovery_code: z
    .string()
    .min(8, "Минимум 8 символов")
    .max(12, "Максимум 12 символов")
    .regex(/^[a-zA-Z0-9]+$/, "Только буквы и цифры"),
});

type LoginFormData = z.infer<typeof loginSchema>;
type TotpFormData = z.infer<typeof totpSchema>;
type RecoveryFormData = z.infer<typeof recoverySchema>;

export function LoginPage() {
  const navigate = useNavigate();
  const { setTokens, setUser } = useAuthStore();
  const [step, setStep] = useState<"credentials" | "totp" | "recovery">("credentials");
  const [challengeToken, setChallengeToken] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(true);

  const loginForm = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const totpForm = useForm<TotpFormData>({
    resolver: zodResolver(totpSchema),
    defaultValues: { code: "" },
  });

  const recoveryForm = useForm<RecoveryFormData>({
    resolver: zodResolver(recoverySchema),
    defaultValues: { recovery_code: "" },
  });

  const applyTokens = (data: { access_token: string; refresh_token: string; user: { id: string; email: string; role: string } }) => {
    // Apply storage choice only on success, so a failed attempt never changes persistence.
    setRememberMe(remember);
    setTokens(data.access_token, data.refresh_token);
    setUser({ id: data.user.id, email: data.user.email, role: data.user.role });
    navigate("/admin/cards");
  };

  const handleLogin = async (data: LoginFormData) => {
    setIsLoading(true);
    try {
      const res = await authApi.login(data);
      const body = res.data;
      if (body.stage === "totp_required") {
        setChallengeToken(body.challenge_token);
        setStep("totp");
      } else {
        applyTokens(body);
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      const msg = error?.response?.data?.detail ?? "Неверный email или пароль";
      loginForm.setError("password", { message: msg });
    } finally {
      setIsLoading(false);
    }
  };

  const handleTotp = async (data: TotpFormData) => {
    setIsLoading(true);
    try {
      const res = await authApi.loginTotp({ challenge_token: challengeToken, code: data.code });
      applyTokens(res.data);
    } catch {
      totpForm.setError("code", { message: "Неверный код. Попробуйте снова." });
    } finally {
      setIsLoading(false);
    }
  };

  const handleRecovery = async (data: RecoveryFormData) => {
    setIsLoading(true);
    try {
      const res = await authApi.loginRecovery({ challenge_token: challengeToken, recovery_code: data.recovery_code });
      applyTokens(res.data);
    } catch {
      recoveryForm.setError("recovery_code", { message: "Неверный резервный код. Попробуйте снова." });
    } finally {
      setIsLoading(false);
    }
  };

  if (step === "recovery") {
    return (
      <AuthShell>
        <h1 className="text-[34px] font-semibold leading-[1.2] mb-6">Резервный код</h1>
        <p className="text-sm text-std-muted mb-6">Введите один из резервных кодов восстановления</p>
        <Form {...recoveryForm}>
          <form onSubmit={recoveryForm.handleSubmit(handleRecovery)} className="space-y-4">
            <FormField
              control={recoveryForm.control}
              name="recovery_code"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-foreground">Резервный код</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="XXXXXXXX"
                      maxLength={12}
                      autoFocus
                      autoComplete="off"
                      className="bg-std-surface-2 rounded-[12px] px-4 py-3 border-0 placeholder:text-std-muted h-12 focus-visible:ring-1"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="flex gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setStep("totp")}
                className="flex-1 h-12 rounded-full font-semibold text-sm"
              >
                Назад
              </Button>
              <Button
                type="submit"
                disabled={isLoading}
                className="flex-1 h-12 rounded-full font-semibold text-sm"
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Войти
              </Button>
            </div>
          </form>
        </Form>
      </AuthShell>
    );
  }

  if (step === "totp") {
    return (
      <AuthShell>
        <h1 className="text-[34px] font-semibold leading-[1.2] mb-6">Двухфакторная аутентификация</h1>
        <p className="text-sm text-std-muted mb-6">Введите код из приложения-аутентификатора</p>
        <Form {...totpForm}>
          <form onSubmit={totpForm.handleSubmit(handleTotp)} className="space-y-4">
            <FormField
              control={totpForm.control}
              name="code"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-foreground">Код</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="000000"
                      maxLength={6}
                      inputMode="numeric"
                      autoFocus
                      autoComplete="one-time-code"
                      className="bg-std-surface-2 rounded-[12px] px-4 py-3 border-0 placeholder:text-std-muted h-12 focus-visible:ring-1"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="flex gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setStep("credentials")}
                className="flex-1 h-12 rounded-full font-semibold text-sm"
              >
                Назад
              </Button>
              <Button
                type="submit"
                disabled={isLoading}
                className="flex-1 h-12 rounded-full font-semibold text-sm"
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Войти
              </Button>
            </div>
            <Button
              type="button"
              variant="link"
              className="w-full text-sm text-muted-foreground"
              onClick={() => { totpForm.reset(); setStep("recovery"); }}
            >
              Использовать резервный код
            </Button>
          </form>
        </Form>
      </AuthShell>
    );
  }

  const isFormFilled = loginForm.watch("email") !== "" && loginForm.watch("password") !== "";

  return (
    <AuthShell>
      <h1 className="text-[40px] font-medium leading-none mb-6 tracking-normal">Вход</h1>
      <Form {...loginForm}>
        <form onSubmit={loginForm.handleSubmit(handleLogin)} className="space-y-4">
          <FormField
            control={loginForm.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm font-medium text-foreground">Email</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    type="email"
                    placeholder="Введите вашу почту"
                    autoComplete="email"
                    className="bg-std-surface-2 rounded-[12px] px-4 py-3 border-0 placeholder:text-std-muted placeholder:font-normal h-12 focus-visible:ring-1"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={loginForm.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <div className="flex items-center justify-between">
                  <FormLabel className="text-sm font-medium text-foreground">Пароль</FormLabel>
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="text-sm text-std-primary hover:opacity-80 transition-opacity"
                  >
                    {showPassword ? "Скрыть" : "Показать"}
                  </button>
                </div>
                <FormControl>
                  <div className="relative">
                    <Input
                      {...field}
                      type={showPassword ? "text" : "password"}
                      placeholder="Введите пароль"
                      autoComplete="current-password"
                      className="bg-std-surface-2 rounded-[12px] px-4 py-3 border-0 placeholder:text-std-muted placeholder:font-normal h-12 focus-visible:ring-1 pr-10"
                    />
                    <Info className="absolute right-3 top-1/2 -translate-y-1/2 size-5 text-muted-foreground pointer-events-none" />
                  </div>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <div className="flex justify-start pt-1">
            <Link to="/forgot-password" className="text-sm text-std-primary hover:underline">
              Забыли пароль?
            </Link>
          </div>
          <div className="flex items-center pt-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <Checkbox
                id="remember"
                checked={remember}
                onCheckedChange={(v) => setRemember(v === true)}
              />
              <span className="text-sm text-foreground">Запомнить меня</span>
            </label>
          </div>
          <Button
            type="submit"
            disabled={isLoading || !isFormFilled}
            className={`w-full h-14 rounded-full font-semibold text-sm mt-2 ${
              isFormFilled
                ? "bg-std-primary text-white hover:bg-std-primary/90"
                : "bg-std-surface-2 text-std-muted cursor-default"
            }`}
          >
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Войти
          </Button>
        </form>
      </Form>
      <p className="text-center text-sm text-foreground mt-6">
        Ещё нет аккаунта?{" "}
        <button
          type="button"
          className="text-std-primary hover:underline bg-transparent border-0 p-0 cursor-pointer"
          onClick={() =>
            alert(
              "Регистрация в системе — по приглашению администратора. Обратитесь в аппарат СТД."
            )
          }
        >
          Зарегистрироваться
        </button>
      </p>
    </AuthShell>
  );
}
