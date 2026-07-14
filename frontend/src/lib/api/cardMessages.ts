import { apiClient } from "./client";

export interface CardMessage {
  id: string;
  card_id: string;
  text: string;
  image_key: string | null;
  created_by: string | null;
  created_at: string;
  deleted_at: string | null;
}

export const cardMessagesApi = {
  list: (cardId: string) =>
    apiClient.get<CardMessage[]>(`/cards/${cardId}/messages`),

  publish: (cardId: string, text: string, file: File | null, deactivate: boolean = true) => {
    const fd = new FormData();
    fd.append("text", text);
    if (file) fd.append("file", file);
    fd.append("deactivate", deactivate ? "true" : "false");
    return apiClient.post<CardMessage>(`/cards/${cardId}/messages`, fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  remove: (cardId: string, messageId: string) =>
    apiClient.delete(`/cards/${cardId}/messages/${messageId}`),
};
