import { apiClient } from "./client";

export type ImportStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export interface ImportRowError {
  row: number;
  error: string;
}

export interface ImportJob {
  id: string;
  created_by: string | null;
  template_id: string | null;
  file_key: string;
  file_name: string;
  status: ImportStatus;
  total_rows: number;
  processed_rows: number;
  inserted_rows: number;
  error_count: number;
  errors_sample: ImportRowError[];
  errors_file_key: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
}

export const importsApi = {
  uploadExcel: (file: File, templateId?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (templateId) form.append("template_id", templateId);
    return apiClient.post<ImportJob>("/import/excel", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  getJob: (id: string) => apiClient.get<ImportJob>(`/import/jobs/${id}`),
  cancelJob: (id: string) => apiClient.post(`/import/jobs/${id}/cancel`),
  downloadTemplate: () =>
    apiClient.get("/import/empty-template.xlsx", { responseType: "blob" }),
};
