import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Loader2, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { authApi, type TotpEnrollResponse } from "@/lib/api/auth";

const verifySchema = z.object({
  code: z.string().length(6, "Код должен быть 6 цифр").regex(/^\d+$/, "Только цифры"),
});

type VerifyFormData = z.infer<typeof verifySchema>;

function extractSecret(otpauthUrl: string): string {
  try {
    const url = new URL(otpauthUrl);
    return url.searchParams.get("secret") ?? otpauthUrl;
  } catch {
    return otpauthUrl;
  }
}

export function TwoFactorSetupPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [step, setStep] = useState<"start" | "scan" | "done">("start");
  const [enrollData, setEnrollData] = useState<TotpEnrollResponse | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const form = useForm<VerifyFormData>({
    resolver: zodResolver(verifySchema),
    defaultValues: { code: "" },
  });

  const handleEnroll = async () => {
    setIsLoading(true);
    try {
      const res = await authApi.totpEnroll();
      setEnrollData(res.data);
      setStep("scan");
    } catch {
      toast.error("Не удалось начать настройку 2FA");
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerify = async (data: VerifyFormData) => {
    setIsLoading(true);
    try {
      const res = await authApi.totpVerify(data.code);
      setRecoveryCodes(res.data.recovery_codes);
      setStep("done");
      toast.success("Двухфакторная аутентификация включена!");
    } catch {
      toast.error("Неверный код. Попробуйте снова.");
      form.reset();
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedCode(text);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  if (step === "done") {
    return (
      <Card className="max-w-lg">
        <CardHeader>
          <CardTitle>2FA включена</CardTitle>
          <CardDescription>
            Двухфакторная аутентификация успешно настроена. При следующем входе потребуется код.
          </CardDescription>
        </CardHeader>
        {recoveryCodes.length > 0 && (
          <CardContent>
            <p className="text-sm font-medium mb-2">Резервные коды (сохраните в надёжном месте):</p>
            <div className="grid grid-cols-2 gap-1">
              {recoveryCodes.map((code) => (
                <div
                  key={code}
                  className="flex items-center justify-between p-1.5 rounded bg-muted font-mono text-xs"
                >
                  {code}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-5 w-5"
                    onClick={() => copyToClipboard(code)}
                  >
                    {copiedCode === code ? (
                      <Check className="h-3 w-3 text-green-500" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        )}
      </Card>
    );
  }

  if (step === "scan" && enrollData) {
    const secret = extractSecret(enrollData.otpauth_url);
    return (
      <Card className="max-w-lg">
        <CardHeader>
          <CardTitle>Настройка 2FA</CardTitle>
          <CardDescription>
            Отсканируйте QR-код приложением аутентификатора (Google Authenticator, Authy и т.д.)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex justify-center">
            <img
              src={`data:image/png;base64,${enrollData.qr_png_base64}`}
              alt="QR код для 2FA"
              className="rounded-lg border p-2"
              width={200}
              height={200}
            />
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-2">Или введите ключ вручную:</p>
            <div className="flex items-center gap-2 p-2 rounded-md bg-muted font-mono text-sm">
              <span className="flex-1 break-all">{secret}</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 shrink-0"
                onClick={() => copyToClipboard(secret)}
              >
                {copiedCode === secret ? (
                  <Check className="h-3 w-3 text-green-500" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </Button>
            </div>
          </div>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleVerify)} className="space-y-4">
              <FormField
                control={form.control}
                name="code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Код подтверждения</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        placeholder="000000"
                        maxLength={6}
                        inputMode="numeric"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" disabled={isLoading} className="w-full">
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Подтвердить
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="max-w-lg">
      <CardHeader>
        <CardTitle>Настройка двухфакторной аутентификации</CardTitle>
        <CardDescription>
          Повысьте безопасность аккаунта с помощью приложения-аутентификатора
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button onClick={handleEnroll} disabled={isLoading}>
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Включить 2FA
        </Button>
      </CardContent>
    </Card>
  );
}
