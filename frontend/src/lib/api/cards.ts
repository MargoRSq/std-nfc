import { apiClient } from "./client";

export interface Category {
  id: number;
  code: string;
  name_ru: string;
  order_idx: number;
  color_hex?: string | null;
}

export interface BackgroundGradient {
  from: string;
  to: string;
  angle: number;
}

export interface CustomField {
  key: string;
  label: string;
  value: string;
  type?: "text" | "number" | "date" | "url" | "phone" | "email";
  is_hidden?: boolean;
  multiline_label?: boolean;
}

export interface ContactBlock {
  type: string | null;
  value: string;
  is_internal?: boolean;
  is_hidden?: boolean;
  label?: string | null;
  input_type?: "text" | "number" | "date" | "url" | "phone" | "email";
}

export interface Card {
  id: string;
  public_slug: string;
  category_id: number;
  template_id?: string | null;
  last_name: string;
  first_name: string;
  middle_name?: string | null;
  full_name_search: string;
  membership_no: string;
  birth_date?: string | null;
  region?: string | null;
  card_issue_date?: string | null;
  join_date?: string | null;
  chairman?: string | null;
  photo_key?: string | null;
  photo_shape: "square" | "circle";
  logo_key?: string | null;
  logo_shape?: "square" | "circle" | "rectangle";
  bg_kind: "solid" | "gradient";
  bg_color?: string | null;
  bg_gradient?: BackgroundGradient | null;
  avatar_color?: string | null;
  avatar_gradient?: BackgroundGradient | null;
  custom_fields: Record<string, unknown>;
  label_set: CustomField[];
  field_order: string[];
  field_labels?: Record<string, string>;
  contacts?: ContactBlock[];
  internal_blocks?: ContactBlock[];
  hide_birth_date?: boolean;
  hide_region?: boolean;
  hide_card_issue_date?: boolean;
  hide_join_date?: boolean;
  hide_chairman?: boolean;
  feedback_form_enabled: boolean;
  created_by?: string | null;
  assigned_admin_id?: string | null;
  is_active: boolean;
  deleted_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CardListItem {
  id: string;
  public_slug: string;
  last_name: string;
  first_name: string;
  middle_name?: string | null;
  membership_no: string;
  category_id: number;
  region?: string | null;
  is_active: boolean;
  photo_key?: string | null;
  birth_date?: string | null;
  bg_kind?: string;
  bg_color?: string | null;
  bg_gradient?: { start: string; end: string; angle?: number } | null;
  template_id?: string | null;
  created_at: string;
}

export interface CardCreateRequest {
  last_name: string;
  first_name: string;
  middle_name?: string;
  membership_no: string;
  category_id?: number;
  template_id?: string;
  birth_date?: string;
  region?: string;
  card_issue_date?: string;
  join_date?: string;
  chairman?: string;
  photo_shape?: "square" | "circle";
  logo_shape?: "square" | "circle" | "rectangle";
  bg_kind?: "solid" | "gradient";
  bg_color?: string;
  bg_gradient?: BackgroundGradient;
  avatar_color?: string | null;
  avatar_gradient?: BackgroundGradient | null;
  custom_fields?: Record<string, unknown>;
  label_set?: CustomField[];
  field_order?: string[];
  field_labels?: Record<string, string>;
  internal_blocks?: ContactBlock[];
  hide_birth_date?: boolean;
  hide_region?: boolean;
  hide_card_issue_date?: boolean;
  hide_join_date?: boolean;
  hide_chairman?: boolean;
  feedback_form_enabled?: boolean;
  public_slug?: string;
  contacts?: ContactBlock[];
  logo_key?: string | null;
}

export interface CardsListResponse {
  items: CardListItem[];
  total: number;
  page: number;
  page_size: number;
}

export type DateField = "added" | "opened" | "modified" | "created" | "issued";

export interface CardsListParams {
  page?: number;
  page_size?: number;
  q?: string;
  category_id?: number;
  region?: string;
  is_active?: boolean;
  sort?: string;
  date_field?: DateField;
  date_from?: string;
  date_to?: string;
}

export const cardsApi = {
  list: (params: CardsListParams = {}) =>
    apiClient.get<CardsListResponse>("/cards/", { params }),
  get: (id: string) => apiClient.get<Card>(`/cards/${id}`),
  create: (data: CardCreateRequest) => apiClient.post<Card>("/cards/", data),
  preview: (data: CardCreateRequest) =>
    apiClient.post<string>("/cards/preview", data, { responseType: "text" }),
  update: (id: string, data: Partial<CardCreateRequest>) =>
    apiClient.patch<Card>(`/cards/${id}`, data),
  delete: (id: string) => apiClient.delete(`/cards/${id}`),
  checkSlug: (slug: string, excludeId?: string) =>
    apiClient.get<{ available: boolean }>("/cards/check-slug", {
      params: { slug, exclude_id: excludeId },
    }),
  regenerateSlug: (id: string) =>
    apiClient.post<{ public_slug: string }>(`/cards/${id}/regenerate-slug`),
  applyTemplate: (id: string, templateId: string) =>
    apiClient.post<Card>(`/cards/${id}/apply-template`, { template_id: templateId }),
  getCategories: () => apiClient.get<Category[]>("/categories/"),
  exportAll: () =>
    apiClient.get<Blob>("/cards/export.xlsx", { responseType: "blob" }),
};
