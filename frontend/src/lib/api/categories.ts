import { apiClient } from "./client";

export interface Category {
  id: number;
  code: string;
  name_ru: string;
  order_idx: number;
  color_hex: string | null;
}

export const categoriesApi = {
  list: () => apiClient.get<Category[]>("/categories/"),
};
