import { apiClient } from "./client";

export interface Admin {
  id: string;
  email: string;
  name?: string | null;
  role: string;
  is_active: boolean;
  totp_enabled: boolean;
  last_login_at: string | null;
  created_at: string;
  allowed_categories: number[];
}

export interface AuditLogEntry {
  id: string;
  actor_id: string;
  actor_email: string;
  action: string;
  entity_type?: string;
  entity_id?: string;
  diff?: Record<string, unknown>;
  ip?: string;
  user_agent?: string;
  ts: string;
}

export interface InviteRequest {
  email: string;
  name?: string;
  role: "admin" | "super_admin";
  category_ids?: number[];
  can_export?: boolean;
  initial_password?: string;
}

export interface UpdateAdminRequest {
  role?: "admin" | "super_admin";
  category_ids?: number[];
}

export interface CreateAdminResponse {
  user: Admin;
  temporary_password: string;
}

export interface ResetPasswordResponse {
  temporary_password: string;
}

export const adminsApi = {
  list: () => apiClient.get<Admin[]>("/admins/"),
  invite: (data: InviteRequest) =>
    apiClient.post<CreateAdminResponse>("/admins/", data),
  resetPassword: (id: string) =>
    apiClient.post<ResetPasswordResponse>(`/admins/${id}/reset-password`),
  resetTotp: (id: string) => apiClient.post(`/admins/${id}/reset-2fa`),
  block: (id: string) =>
    apiClient.patch(`/admins/${id}`, { is_active: false }),
  unblock: (id: string) =>
    apiClient.patch(`/admins/${id}`, { is_active: true }),
  update: (id: string, data: UpdateAdminRequest) =>
    apiClient.patch<Admin>(`/admins/${id}`, data),
  delete: (id: string) => apiClient.delete(`/admins/${id}`),
  auditLog: (params?: {
    actor_id?: string;
    action?: string;
    entity_type?: string;
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  }) =>
    apiClient.get<{ items: AuditLogEntry[]; total: number; page: number; page_size: number }>(
      "/admins/audit",
      { params },
    ),
};
