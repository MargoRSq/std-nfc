import { apiClient } from "./client";
import type { ContactBlock } from "@/components/cards/ContactBlocksEditor";

/** Регион, чьи контакты показываются всем, у кого нет своей записи. */
export const DEFAULT_REGION = "*";

export interface RegionContacts {
  id: number;
  region: string;
  contacts: ContactBlock[];
  created_at: string;
  updated_at: string;
}

export const regionContactsApi = {
  list: () => apiClient.get<RegionContacts[]>("/region-contacts/"),
  upsert: (region: string, contacts: ContactBlock[]) =>
    apiClient.put<RegionContacts>(`/region-contacts/${encodeURIComponent(region)}`, { contacts }),
  remove: (region: string) =>
    apiClient.delete<void>(`/region-contacts/${encodeURIComponent(region)}`),
};
