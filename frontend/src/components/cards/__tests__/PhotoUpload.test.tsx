import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PhotoUpload } from "../PhotoUpload";

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/lib/api/client", () => ({
  apiClient: { post: vi.fn() },
}));

describe("PhotoUpload", () => {
  it("renders img when initialKey is provided", () => {
    const { container } = render(
      <PhotoUpload
        cardId="card-1"
        initialKey="media/photo-key.jpg"
        onUploaded={vi.fn()}
      />,
    );

    const img = container.querySelector("img");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "/api/media/media/photo-key.jpg");
  });

  it("shows upload button text when no key", () => {
    render(<PhotoUpload cardId="card-1" initialKey={null} onUploaded={vi.fn()} />);

    expect(screen.getByRole("button", { name: /загрузить/i })).toBeInTheDocument();
  });

  it("shows replace button text when key exists", () => {
    render(
      <PhotoUpload cardId="card-1" initialKey="some-key" onUploaded={vi.fn()} />,
    );

    expect(screen.getByRole("button", { name: /заменить/i })).toBeInTheDocument();
  });

  it("clicking button triggers hidden file input click", () => {
    render(<PhotoUpload cardId="card-1" initialKey={null} onUploaded={vi.fn()} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const clickSpy = vi.spyOn(input, "click");

    fireEvent.click(screen.getByRole("button", { name: /загрузить/i }));

    expect(clickSpy).toHaveBeenCalled();
  });
});
