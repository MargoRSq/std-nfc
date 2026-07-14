import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ApproveSaveModal, type DiffEntry } from "../ApproveSaveModal";
import { QuitConfirmModal } from "../QuitConfirmModal";
import { SaveSuccessModal } from "../SaveSuccessModal";

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = globalThis.ResizeObserver ?? ResizeObserverMock;

const diffs: DiffEntry[] = [
  { label: "Фамилия", before: "Иванов", after: "Петров" },
  { label: "Дата выдачи билета", before: "2025-01-01", after: "2026-01-01" },
];

describe("ApproveSaveModal", () => {
  it("renders diffs and calls onConfirm", async () => {
    const onConfirm = vi.fn();
    const user = userEvent.setup();
    render(<ApproveSaveModal open={true} diffs={diffs} onConfirm={onConfirm} onCancel={vi.fn()} />);
    expect(screen.getByText("Фамилия")).toBeInTheDocument();
    expect(screen.getByText("Дата выдачи билета")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /сохранить/i }));
    expect(onConfirm).toHaveBeenCalled();
  });
});

describe("QuitConfirmModal", () => {
  it("destructive proceed button triggers callback", async () => {
    const onProceed = vi.fn();
    const user = userEvent.setup();
    render(<QuitConfirmModal open={true} onProceed={onProceed} onCancel={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: /выйти без сохранения/i }));
    expect(onProceed).toHaveBeenCalled();
  });

  it("cancel triggers callback", async () => {
    const onCancel = vi.fn();
    const user = userEvent.setup();
    render(<QuitConfirmModal open={true} onProceed={vi.fn()} onCancel={onCancel} />);
    await user.click(screen.getByRole("button", { name: /остаться/i }));
    expect(onCancel).toHaveBeenCalled();
  });
});

describe("SaveSuccessModal", () => {
  it("shows title and home button", () => {
    render(
      <MemoryRouter>
        <SaveSuccessModal open={true} title="Карточка сохранена!" onClose={vi.fn()} />
      </MemoryRouter>,
    );
    expect(screen.getByText("Карточка сохранена!")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /вернуться на главную/i })).toBeInTheDocument();
  });
});
