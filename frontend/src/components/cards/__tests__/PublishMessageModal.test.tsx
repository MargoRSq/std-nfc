import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PublishMessageModal } from "../PublishMessageModal";

const publishMock = vi.fn();
vi.mock("@/lib/api/cardMessages", () => ({
  cardMessagesApi: {
    publish: (...a: unknown[]) => publishMock(...a),
    list: vi.fn(),
    remove: vi.fn(),
  },
}));

const toastSuccess = vi.fn();
const toastError = vi.fn();
vi.mock("sonner", () => ({
  toast: {
    success: (...a: unknown[]) => toastSuccess(...a),
    error: (...a: unknown[]) => toastError(...a),
  },
}));

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = globalThis.ResizeObserver ?? ResizeObserverMock;

function renderModal(cardId: string | null = "card-1") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PublishMessageModal cardId={cardId} open={true} onOpenChange={() => {}} />
    </QueryClientProvider>,
  );
}

describe("PublishMessageModal", () => {
  beforeEach(() => {
    publishMock.mockReset();
    toastSuccess.mockReset();
    toastError.mockReset();
  });

  it("renders title and CTA", () => {
    renderModal();
    expect(screen.getByText("Опубликовать сообщение?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /опубликовать/i })).toBeInTheDocument();
  });

  it("rejects empty submission", async () => {
    const user = userEvent.setup();
    renderModal();
    await user.click(screen.getByRole("button", { name: /опубликовать/i }));
    expect(screen.getByText("Введите текст или прикрепите изображение")).toBeInTheDocument();
    expect(publishMock).not.toHaveBeenCalled();
  });

  it("publishes text-only message", async () => {
    const user = userEvent.setup();
    publishMock.mockResolvedValue({ data: { id: "msg-1" } });
    renderModal();
    await user.type(screen.getByPlaceholderText(/введите текст сообщения/i), "Hello");
    await user.click(screen.getByRole("button", { name: /опубликовать/i }));
    await waitFor(() => {
      expect(publishMock).toHaveBeenCalledWith("card-1", "Hello", null);
      expect(toastSuccess).toHaveBeenCalled();
    });
  });

  it("rejects file >5MB", async () => {
    const user = userEvent.setup();
    renderModal();
    const big = new File([new Uint8Array(6 * 1024 * 1024)], "big.jpg", {
      type: "image/jpeg",
    });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, big);
    expect(screen.getByText(/больше 5/i)).toBeInTheDocument();
  });
});
