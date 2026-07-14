import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { UserPlus, Shield, Lock, ShieldOff, Trash2, Eye, EyeOff, Pencil, Search } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
import { adminsApi, type Admin, type InviteRequest } from "@/lib/api/admins";
import { cardsApi, type Category } from "@/lib/api/cards";
import { useDebounce } from "@/hooks/useDebounce";

const ADMINS_PAGE_SIZE = 10;

type PermissionScope = "all" | "group" | "card";

function getPermissionLabel(admin: Admin): string {
  if (admin.role === "super_admin") return "Все карточки";
  if (admin.allowed_categories && admin.allowed_categories.length > 0) return "Группа";
  return "—";
}

function getAdminInitials(email: string): string {
  const local = email.split("@")[0];
  const parts = local.split(/[._-]/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return local.slice(0, 2).toUpperCase();
}

function buildPageNumbers(current: number, total: number): (number | "...")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages: (number | "...")[] = [1];
  if (current > 3) pages.push("...");
  for (let p = Math.max(2, current - 1); p <= Math.min(total - 1, current + 1); p++) {
    pages.push(p);
  }
  if (current < total - 2) pages.push("...");
  pages.push(total);
  return pages;
}

const inviteSchema = z.object({
  email: z.string().email("Некорректный email"),
  name: z.string().optional(),
  scope: z.enum(["all", "group", "card"] as const),
  category_ids: z.array(z.number()).optional(),
});

type InviteFormData = z.infer<typeof inviteSchema>;

const editPermissionsSchema = z.object({
  scope: z.enum(["all", "group", "card"] as const),
  category_ids: z.array(z.number()).optional(),
});

type EditPermissionsFormData = z.infer<typeof editPermissionsSchema>;

function PermissionScopeSelector({
  value,
  onChange,
  categories,
  selectedCategories,
  onCategoriesChange,
}: {
  value: PermissionScope;
  onChange: (v: PermissionScope) => void;
  categories: Category[];
  selectedCategories: number[];
  onCategoriesChange: (ids: number[]) => void;
}) {
  const options: { value: PermissionScope; label: string; description: string }[] = [
    { value: "all", label: "Все карточки", description: "Полный доступ ко всем карточкам" },
    { value: "group", label: "Группа", description: "Доступ к выбранным категориям" },
    { value: "card", label: "Карточка", description: "Доступ к конкретным карточкам" },
  ];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={[
              "rounded-lg border p-3 text-left transition-colors",
              value === opt.value
                ? "border-primary bg-primary/5"
                : "border-border hover:border-muted-foreground/50",
            ].join(" ")}
          >
            <div className="text-sm font-medium">{opt.label}</div>
            <div className="text-xs text-muted-foreground mt-0.5">{opt.description}</div>
          </button>
        ))}
      </div>

      {value === "group" && categories.length > 0 && (
        <div className="space-y-2 rounded-lg border p-3 max-h-48 overflow-y-auto">
          {categories.map((cat) => (
            <label key={cat.id} className="flex items-center gap-2 cursor-pointer">
              <Checkbox
                checked={selectedCategories.includes(cat.id)}
                onCheckedChange={(checked) => {
                  if (checked) {
                    onCategoriesChange([...selectedCategories, cat.id]);
                  } else {
                    onCategoriesChange(selectedCategories.filter((id) => id !== cat.id));
                  }
                }}
              />
              <span className="text-sm">{cat.name_ru}</span>
            </label>
          ))}
        </div>
      )}

      {value === "card" && (
        <p className="text-xs text-muted-foreground">
          Доступ к конкретным карточкам настраивается в разделе карточек.
        </p>
      )}
    </div>
  );
}

export function AdminsPage() {
  const qc = useQueryClient();
  const [inviteOpen, setInviteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [createdPassword, setCreatedPassword] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [resetPassword, setResetPassword] = useState<string | null>(null);
  const [editTarget, setEditTarget] = useState<Admin | null>(null);

  const [inviteScope, setInviteScope] = useState<PermissionScope>("all");
  const [inviteCategoryIds, setInviteCategoryIds] = useState<number[]>([]);

  const [editScope, setEditScope] = useState<PermissionScope>("all");
  const [editCategoryIds, setEditCategoryIds] = useState<number[]>([]);

  const [searchRaw, setSearchRaw] = useState("");
  const searchQuery = useDebounce(searchRaw, 300);
  const [adminsPage, setAdminsPage] = useState(1);

  const { data: admins, isLoading } = useQuery({
    queryKey: ["admins"],
    queryFn: () => adminsApi.list().then((r) => r.data),
  });

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: () => cardsApi.getCategories().then((r) => r.data),
  });

  const filteredAdmins = useMemo(() => {
    if (!admins) return [];
    if (!searchQuery.trim()) return admins;
    const q = searchQuery.toLowerCase();
    return admins.filter((a) => a.email.toLowerCase().includes(q));
  }, [admins, searchQuery]);

  const adminsTotalPages = Math.max(1, Math.ceil(filteredAdmins.length / ADMINS_PAGE_SIZE));
  const pagedAdmins = filteredAdmins.slice(
    (adminsPage - 1) * ADMINS_PAGE_SIZE,
    adminsPage * ADMINS_PAGE_SIZE,
  );

  const inviteMutation = useMutation({
    mutationFn: (data: InviteRequest) => adminsApi.invite(data),
    onSuccess: (res) => {
      setCreatedPassword(res.data.temporary_password);
      void qc.invalidateQueries({ queryKey: ["admins"] });
      setInviteOpen(false);
      inviteForm.reset();
      setInviteScope("all");
      setInviteCategoryIds([]);
    },
    onError: () => toast.error("Ошибка при создании администратора"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { role: "admin" | "super_admin"; category_ids?: number[] } }) =>
      adminsApi.update(id, data),
    onSuccess: () => {
      toast.success("Права обновлены");
      void qc.invalidateQueries({ queryKey: ["admins"] });
      setEditTarget(null);
    },
    onError: () => toast.error("Ошибка при обновлении прав"),
  });

  const blockMutation = useMutation({
    mutationFn: ({ id, blocked }: { id: string; blocked: boolean }) =>
      blocked ? adminsApi.unblock(id) : adminsApi.block(id),
    onSuccess: () => {
      toast.success("Статус обновлён");
      void qc.invalidateQueries({ queryKey: ["admins"] });
    },
    onError: () => toast.error("Ошибка"),
  });

  const resetPasswordMutation = useMutation({
    mutationFn: (id: string) => adminsApi.resetPassword(id),
    onSuccess: (res) => {
      setResetPassword(res.data.temporary_password);
    },
    onError: () => toast.error("Ошибка"),
  });

  const resetTotpMutation = useMutation({
    mutationFn: (id: string) => adminsApi.resetTotp(id),
    onSuccess: () => toast.success("2FA сброшена"),
    onError: () => toast.error("Ошибка"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminsApi.delete(id),
    onSuccess: () => {
      toast.success("Администратор удалён");
      void qc.invalidateQueries({ queryKey: ["admins"] });
    },
    onError: () => toast.error("Ошибка при удалении"),
  });

  const inviteForm = useForm<InviteFormData>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { email: "", name: "", scope: "all", category_ids: [] },
  });

  const editForm = useForm<EditPermissionsFormData>({
    resolver: zodResolver(editPermissionsSchema),
    defaultValues: { scope: "all", category_ids: [] },
  });

  function handleInviteSubmit(d: InviteFormData) {
    const role: "admin" | "super_admin" = inviteScope === "all" ? "super_admin" : "admin";
    const category_ids = inviteScope === "group" ? inviteCategoryIds : undefined;
    inviteMutation.mutate({ email: d.email, name: d.name || undefined, role, category_ids });
  }

  function openEditModal(admin: Admin) {
    setEditTarget(admin);
    const scope: PermissionScope =
      admin.role === "super_admin" ? "all" :
      admin.allowed_categories && admin.allowed_categories.length > 0 ? "group" : "card";
    setEditScope(scope);
    setEditCategoryIds(admin.allowed_categories ?? []);
    editForm.reset({ scope, category_ids: admin.allowed_categories ?? [] });
  }

  function handleEditSubmit() {
    if (!editTarget) return;
    const role: "admin" | "super_admin" = editScope === "all" ? "super_admin" : "admin";
    const category_ids = editScope === "group" ? editCategoryIds : undefined;
    updateMutation.mutate({ id: editTarget.id, data: { role, category_ids } });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Администраторы</h1>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Поиск"
              value={searchRaw}
              onChange={(e) => { setSearchRaw(e.target.value); setAdminsPage(1); }}
              className="pl-9 w-52"
            />
          </div>
          <Button onClick={() => setInviteOpen(true)} className="w-full sm:w-auto">
            Добавить администратора
            <UserPlus className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="hidden md:block rounded-lg border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ФИО</TableHead>
              <TableHead>Почта</TableHead>
              <TableHead>Статус</TableHead>
              <TableHead>Права</TableHead>
              <TableHead>Дата назначения</TableHead>
              <TableHead className="text-right">Действия</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 6 }).map((_, j) => (
                    <TableCell key={j}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : !pagedAdmins.length ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-10 text-muted-foreground">
                  {searchQuery ? "Ничего не найдено" : "Администраторов нет"}
                </TableCell>
              </TableRow>
            ) : (
              pagedAdmins.map((admin) => (
                <TableRow key={admin.id}>
                  <TableCell className="font-medium text-muted-foreground">{admin.name || "—"}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{admin.email}</TableCell>
                  <TableCell className="text-sm font-medium">
                    {admin.is_active ? (
                      <span className="text-std-status-active">Активен</span>
                    ) : (
                      <span className="text-std-status-blocked">Заблокирован</span>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {getPermissionLabel(admin)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {format(new Date(admin.created_at), "dd.MM.yyyy", { locale: ru })}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="outline" size="icon" aria-label="Действия с администратором" className="h-8 w-8 rounded-md">
                          <Pencil className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => openEditModal(admin)}>
                          <Pencil className="mr-2 h-4 w-4" />
                          Изменить права
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => resetPasswordMutation.mutate(admin.id)}>
                          <Lock className="mr-2 h-4 w-4" />
                          Сбросить пароль
                        </DropdownMenuItem>
                        {admin.totp_enabled && (
                          <DropdownMenuItem onClick={() => resetTotpMutation.mutate(admin.id)}>
                            <Shield className="mr-2 h-4 w-4" />
                            Сбросить 2FA
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuItem
                          onClick={() =>
                            blockMutation.mutate({ id: admin.id, blocked: !admin.is_active })
                          }
                        >
                          <ShieldOff className="mr-2 h-4 w-4" />
                          {admin.is_active ? "Заблокировать" : "Активировать"}
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-destructive focus:text-destructive"
                          onClick={() => setDeleteTarget(admin.id)}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Удалить
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="md:hidden flex flex-col gap-3">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-[88px] rounded-2xl" />
          ))
        ) : !pagedAdmins.length ? (
          <div className="py-16 text-center text-muted-foreground">
            {searchQuery ? "Ничего не найдено" : "Администраторов нет"}
          </div>
        ) : (
          pagedAdmins.map((admin) => (
            <div
              key={admin.id}
              className="bg-white rounded-2xl border border-std-border p-4 flex gap-3"
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-std-surface-2 text-sm font-semibold text-std-primary">
                {getAdminInitials(admin.email)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <span className="font-semibold text-std-ink-strong text-sm truncate">{admin.email}</span>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" aria-label="Действия с администратором" className="h-7 w-7 -mt-1 -mr-1 shrink-0">
                        <Pencil className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => openEditModal(admin)}>
                        <Pencil className="mr-2 h-4 w-4" />
                        Изменить права
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => resetPasswordMutation.mutate(admin.id)}>
                        <Lock className="mr-2 h-4 w-4" />
                        Сбросить пароль
                      </DropdownMenuItem>
                      {admin.totp_enabled && (
                        <DropdownMenuItem onClick={() => resetTotpMutation.mutate(admin.id)}>
                          <Shield className="mr-2 h-4 w-4" />
                          Сбросить 2FA
                        </DropdownMenuItem>
                      )}
                      <DropdownMenuItem
                        onClick={() =>
                          blockMutation.mutate({ id: admin.id, blocked: !admin.is_active })
                        }
                      >
                        <ShieldOff className="mr-2 h-4 w-4" />
                        {admin.is_active ? "Заблокировать" : "Активировать"}
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        className="text-destructive focus:text-destructive"
                        onClick={() => setDeleteTarget(admin.id)}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Удалить
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                <p className="text-xs text-std-muted-fg mt-1 truncate">
                  {admin.is_active ? (
                    <span className="text-std-status-active font-medium">Активен</span>
                  ) : (
                    <span className="text-std-status-blocked font-medium">Заблокирован</span>
                  )}
                  {" · "}
                  {getPermissionLabel(admin)}
                  {" · "}
                  {format(new Date(admin.created_at), "dd.MM.yyyy", { locale: ru })}
                </p>
              </div>
            </div>
          ))
        )}
      </div>

      {adminsTotalPages > 1 && (
        <div className="flex justify-center items-center gap-1 mt-2">
          <Button
            variant="ghost"
            size="sm"
            disabled={adminsPage <= 1}
            onClick={() => setAdminsPage((p) => p - 1)}
            className="text-sm"
          >
            ← Назад
          </Button>
          {buildPageNumbers(adminsPage, adminsTotalPages).map((item, i) =>
            item === "..." ? (
              <span key={`ellipsis-${i}`} className="px-1 text-sm text-muted-foreground select-none">…</span>
            ) : (
              <button
                key={item}
                type="button"
                onClick={() => setAdminsPage(item as number)}
                className={[
                  "min-w-[32px] h-8 px-2 rounded text-sm transition-colors",
                  item === adminsPage
                    ? "bg-std-primary text-white font-medium"
                    : "text-muted-foreground hover:bg-std-surface-2",
                ].join(" ")}
              >
                {item}
              </button>
            )
          )}
          <Button
            variant="ghost"
            size="sm"
            disabled={adminsPage >= adminsTotalPages}
            onClick={() => setAdminsPage((p) => p + 1)}
            className="text-sm"
          >
            Дальше →
          </Button>
        </div>
      )}

      {/* Invite modal */}
      <Dialog open={inviteOpen} onOpenChange={(o) => { setInviteOpen(o); if (!o) { inviteForm.reset(); setInviteScope("all"); setInviteCategoryIds([]); } }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Добавить администратора</DialogTitle>
          </DialogHeader>
          <Form {...inviteForm}>
            <form onSubmit={inviteForm.handleSubmit(handleInviteSubmit)} className="space-y-4">
              <FormField
                control={inviteForm.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email *</FormLabel>
                    <FormControl>
                      <Input {...field} type="email" placeholder="admin@example.com" autoFocus />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={inviteForm.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Имя</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder="Иван Иванов" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="space-y-2">
                <label className="text-sm font-medium">Права доступа</label>
                <PermissionScopeSelector
                  value={inviteScope}
                  onChange={setInviteScope}
                  categories={categories}
                  selectedCategories={inviteCategoryIds}
                  onCategoriesChange={setInviteCategoryIds}
                />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setInviteOpen(false)}>
                  Отмена
                </Button>
                <Button type="submit" disabled={inviteMutation.isPending}>
                  Добавить
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Edit permissions modal */}
      <Dialog open={!!editTarget} onOpenChange={(o) => !o && setEditTarget(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Изменить права</DialogTitle>
          </DialogHeader>
          {editTarget && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">{editTarget.email}</p>
              <PermissionScopeSelector
                value={editScope}
                onChange={setEditScope}
                categories={categories}
                selectedCategories={editCategoryIds}
                onCategoriesChange={setEditCategoryIds}
              />
              <DialogFooter>
                <Button variant="outline" onClick={() => setEditTarget(null)}>
                  Отмена
                </Button>
                <Button onClick={handleEditSubmit} disabled={updateMutation.isPending}>
                  Сохранить
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Created password modal */}
      <Dialog open={!!createdPassword} onOpenChange={(o) => !o && setCreatedPassword(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Администратор создан</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Передайте временный пароль администратору. После первого входа он сможет его сменить.
          </p>
          <div className="flex items-center gap-2 p-3 rounded-md bg-muted font-mono text-sm">
            <span className="flex-1">{showPassword ? createdPassword : "••••••••••••"}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setShowPassword((v) => !v)}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </Button>
          </div>
          <DialogFooter>
            <Button onClick={() => { setCreatedPassword(null); setShowPassword(false); }}>
              Закрыть
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset password modal */}
      <Dialog open={!!resetPassword} onOpenChange={(o) => !o && setResetPassword(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Пароль сброшен</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">Новый временный пароль:</p>
          <div className="flex items-center gap-2 p-3 rounded-md bg-muted font-mono text-sm">
            <span className="flex-1">{showPassword ? resetPassword : "••••••••••••"}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setShowPassword((v) => !v)}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </Button>
          </div>
          <DialogFooter>
            <Button onClick={() => { setResetPassword(null); setShowPassword(false); }}>
              Закрыть
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить администратора?</AlertDialogTitle>
            <AlertDialogDescription>Это действие нельзя отменить.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Отмена</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground"
              onClick={() => {
                if (deleteTarget) deleteMutation.mutate(deleteTarget);
                setDeleteTarget(null);
              }}
            >
              Удалить
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
