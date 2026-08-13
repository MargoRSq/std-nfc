import { apiClient } from "./client";

export interface Category {
  id: number;
  code: string;
  name_ru: string;
  order_idx: number;
  color_hex: string | null;
  is_hidden: boolean;
  cards_count: number;
  templates_count: number;
}

export interface CategoryUpdateRequest {
  name_ru?: string;
  color_hex?: string;
  is_hidden?: boolean;
}

export const categoriesApi = {
  list: () => apiClient.get<Category[]>("/categories/"),
  update: (id: number, data: CategoryUpdateRequest) =>
    apiClient.patch<Category>(`/categories/${id}`, data),
};

/** Категории для фильтров: без скрытых и без тех, где нет ни карточек, ни шаблонов. */
export function usableCategories(categories: Category[] | undefined, keepId?: number | null) {
  return (categories ?? []).filter(
    (c) =>
      c.id === keepId || (!c.is_hidden && (c.cards_count > 0 || c.templates_count > 0)),
  );
}
