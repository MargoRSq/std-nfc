import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DateFilterDropdown, type DateFilterValue } from "../DateFilterDropdown";

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = globalThis.ResizeObserver ?? ResizeObserverMock;

describe("DateFilterDropdown", () => {
  let onApply: ReturnType<typeof vi.fn>;
  beforeEach(() => {
    onApply = vi.fn();
  });

  it("opens with 4 date field radios", async () => {
    const user = userEvent.setup();
    render(<DateFilterDropdown value={null} onApply={onApply} />);
    await user.click(screen.getByRole("button", { name: /по дате/i }));
    expect(screen.getAllByText("По дате добавления")).toHaveLength(2);
    expect(screen.getByText("По дате последнего открытия")).toBeInTheDocument();
    expect(screen.getByText("По дате изменения")).toBeInTheDocument();
    expect(screen.getByText("По дате создания")).toBeInTheDocument();
  });

  it("apply with empty range calls onApply(null)", async () => {
    const user = userEvent.setup();
    render(<DateFilterDropdown value={null} onApply={onApply} />);
    await user.click(screen.getByRole("button"));
    await user.click(screen.getByRole("button", { name: /применить/i }));
    expect(onApply).toHaveBeenCalledWith(null);
  });

  it("reset clears and calls onApply(null)", async () => {
    const user = userEvent.setup();
    const value: DateFilterValue = {
      field: "added",
      from: "2025-01-01",
      to: "2026-01-01",
    };
    render(<DateFilterDropdown value={value} onApply={onApply} />);
    await user.click(screen.getByRole("button"));
    await user.click(screen.getByRole("button", { name: /сбросить/i }));
    expect(onApply).toHaveBeenCalledWith(null);
  });
});
