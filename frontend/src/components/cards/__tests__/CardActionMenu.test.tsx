import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { CardActionMenu } from "../CardActionMenu";

const toastInfo = vi.fn();

vi.mock("sonner", () => ({
  toast: { info: (...a: unknown[]) => toastInfo(...a) },
}));

const navigate = vi.fn();
vi.mock("react-router-dom", async (orig) => {
  const actual = await orig<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => navigate };
});

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = globalThis.ResizeObserver ?? ResizeObserverMock;

const baseCard = { id: "card-1", public_slug: "abc123" };

function renderMenu(props: Partial<Parameters<typeof CardActionMenu>[0]> = {}) {
  const onDelete = props.onDelete ?? vi.fn();
  const utils = render(
    <MemoryRouter>
      <CardActionMenu card={baseCard} onDelete={onDelete} {...props} />
    </MemoryRouter>,
  );
  return { onDelete, ...utils };
}

async function openMenu(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /действия/i }));
}

describe("CardActionMenu", () => {
  beforeEach(() => {
    navigate.mockReset();
    toastInfo.mockReset();
  });

  it("renders 5 menu items per Figma when opened", async () => {
    const user = userEvent.setup();
    renderMenu();
    await openMenu(user);
    expect(screen.getByRole("menuitem", { name: /посмотреть карточку/i })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /назначить шаблон/i })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /редактировать/i })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /опубликовать сообщение/i })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /удалить/i })).toBeInTheDocument();
  });

  it('"Посмотреть карточку" opens public slug in new tab', async () => {
    const user = userEvent.setup();
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    renderMenu();
    await openMenu(user);
    await user.click(screen.getByRole("menuitem", { name: /посмотреть карточку/i }));
    expect(openSpy).toHaveBeenCalledWith("/c/abc123", "_blank", "noopener,noreferrer");
    openSpy.mockRestore();
  });

  it('"Редактировать" navigates to edit route', async () => {
    const user = userEvent.setup();
    renderMenu();
    await openMenu(user);
    await user.click(screen.getByRole("menuitem", { name: /редактировать/i }));
    expect(navigate).toHaveBeenCalledWith("/admin/cards/card-1/edit");
  });

  it('"Удалить" calls onDelete with id', async () => {
    const user = userEvent.setup();
    const { onDelete } = renderMenu();
    await openMenu(user);
    await user.click(screen.getByRole("menuitem", { name: /удалить/i }));
    expect(onDelete).toHaveBeenCalledWith("card-1");
  });

  it('"Назначить шаблон" without handler shows toast.info', async () => {
    const user = userEvent.setup();
    renderMenu();
    await openMenu(user);
    await user.click(screen.getByRole("menuitem", { name: /назначить шаблон/i }));
    expect(toastInfo).toHaveBeenCalled();
  });

  it('"Опубликовать сообщение" calls handler when provided', async () => {
    const user = userEvent.setup();
    const onPublishMessage = vi.fn();
    renderMenu({ onPublishMessage });
    await openMenu(user);
    await user.click(screen.getByRole("menuitem", { name: /опубликовать сообщение/i }));
    expect(onPublishMessage).toHaveBeenCalledWith("card-1");
  });
});
