import { createElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const testState = vi.hoisted(() => ({
  toggleProfileSettingsModal: vi.fn(),
  menuItems: [] as Array<{ label: string; onClick?: () => void }>,
}));

// Capture the menu options and modal action without mounting the full application shell.
// These mocks keep the test focused on the user-menu behavior under change.
vi.mock("mobx-react", () => ({ observer: (component: unknown) => component }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@makeplane/propel/icons", () => {
  return { LogOutOutline: () => null, SettingsOutline: () => null };
});
vi.mock("@makeplane/propel/components/avatar", () => ({ Avatar: () => null }));
vi.mock("@plane/constants", () => ({ GOD_MODE_URL: "/god-mode/" }));
vi.mock("@plane/i18n", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock("@plane/propel/toast", () => ({ TOAST_TYPE: { ERROR: "error" }, setToast: vi.fn() }));
vi.mock("@plane/utils", () => ({ getFileURL: (url: string) => url }));

// The menu double records each rendered label and callback so we can test the visible choices.
vi.mock("@plane/ui", async () => {
  const React = await import("react");
  const MenuItem = ({ children, onClick }: { children: ReactNode; onClick?: () => void }) => {
    const label = Array.isArray(children) ? children.find((child) => typeof child === "string") : children;
    testState.menuItems.push({ label: typeof label === "string" ? label : "", onClick });
    return React.createElement("button", { onClick, role: "menuitem" }, children);
  };
  const CustomMenu = ({ children, customButton }: { children: ReactNode; customButton: ReactNode }) =>
    React.createElement("div", null, customButton, children);
  Object.assign(CustomMenu, { MenuItem });
  return { CustomMenu };
});
vi.mock("@/components/common/cover-image", () => ({ CoverImage: () => null }));
vi.mock("@/components/sidebar/sidebar-item", () => ({ AppSidebarItem: () => null }));

// Supply predictable user and store state; no API calls or real session are needed.
vi.mock("@/hooks/store/use-app-theme", () => ({ useAppTheme: () => ({ toggleAnySidebarDropdown: vi.fn() }) }));
vi.mock("@/hooks/store/use-command-palette", () => ({
  useCommandPalette: () => ({ toggleProfileSettingsModal: testState.toggleProfileSettingsModal }),
}));
vi.mock("@/hooks/store/user", () => ({
  useUser: () => ({
    data: {
      display_name: "Test User",
      first_name: "Test",
      last_name: "User",
      email: "test@example.com",
    },
    signOut: vi.fn(),
  }),
}));

import { UserMenuRoot } from "@/components/workspace/sidebar/user-menu-root";

describe("UserMenuRoot", () => {
  beforeEach(() => {
    testState.menuItems.length = 0;
    testState.toggleProfileSettingsModal.mockClear();
  });

  it("offers one Settings entry and opens the General tab", () => {
    // Server rendering runs the component and lets the menu double capture its entries.
    renderToStaticMarkup(createElement(UserMenuRoot));

    // Preferences should no longer be a separate avatar-menu action.
    expect(testState.menuItems.map(({ label }) => label)).toEqual(["settings", "sign_out"]);

    // The remaining Settings action still opens the expected default tab.
    testState.menuItems[0]?.onClick?.();
    expect(testState.toggleProfileSettingsModal).toHaveBeenCalledWith({
      activeTab: "general",
      isOpen: true,
    });
  });
});
