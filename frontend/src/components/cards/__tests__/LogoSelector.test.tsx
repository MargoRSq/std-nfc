import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LogoSelector } from "../LogoSelector";

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/lib/api/client", () => ({
  apiClient: { post: vi.fn() },
}));

describe("LogoSelector", () => {
  it("highlights std preset when value is preset:std", () => {
    render(<LogoSelector value="preset:std" cardId="c1" onChange={vi.fn()} />);
    const tile = screen.getByRole("button", { name: /СТД РФ/i });
    expect(tile).toHaveAttribute("aria-pressed", "true");
  });

  it("does not highlight any preset when value is uploaded", () => {
    render(
      <LogoSelector value="cards/abc/logo-deadbeef.webp" cardId="c1" onChange={vi.fn()} />,
    );
    const stdTile = screen.getByRole("button", { name: /СТД РФ/i });
    expect(stdTile).toHaveAttribute("aria-pressed", "false");
  });

  it("renders uploaded logo as additional selected tile", () => {
    const { container } = render(
      <LogoSelector value="cards/abc/logo-x.webp" cardId="c1" onChange={vi.fn()} />,
    );
    const uploadedImg = container.querySelector('img[alt="Загруженный логотип"]');
    expect(uploadedImg).toBeInTheDocument();
    expect(uploadedImg).toHaveAttribute("src", "/api/media/cards/abc/logo-x.webp");
  });

  it("calls onChange with preset:std when std tile clicked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LogoSelector value={null} cardId="c1" onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: /СТД РФ/i }));
    expect(onChange).toHaveBeenCalledWith("preset:std");
  });

  it("calls onChange with null when Удалить clicked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LogoSelector value="preset:std" cardId="c1" onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: /удалить/i }));
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("disables Удалить when value is already null", () => {
    render(<LogoSelector value={null} cardId="c1" onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: /удалить/i })).toBeDisabled();
  });

  it("disables upload when no cardId (create mode)", () => {
    render(<LogoSelector value="preset:std" onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: /загрузить логотип/i })).toBeDisabled();
  });

  it("enables upload when cardId provided", () => {
    render(<LogoSelector value="preset:std" cardId="c1" onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: /загрузить логотип/i })).toBeEnabled();
  });
});
