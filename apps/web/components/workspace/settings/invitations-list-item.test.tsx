/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { IWorkspaceMemberInvitation } from "@plane/types";
import { WorkspaceInvitationsListItem } from "./invitations-list-item";
import { WorkspaceMembersList } from "./members-list";

const mocks = vi.hoisted(() => ({
  role: 20,
  invitation: undefined as IWorkspaceMemberInvitation | undefined,
  resend: vi.fn<(slug: string, id: string) => Promise<void>>(),
  toast: vi.fn(),
}));

vi.mock("next/navigation", () => ({ useParams: () => ({ workspaceSlug: "test-workspace" }) }));
vi.mock("@/hooks/store/use-member", () => ({
  useMember: () => ({
    workspace: {
      getWorkspaceInvitationDetails: () => mocks.invitation,
      resendMemberInvitation: mocks.resend,
      workspaceMemberIds: [],
      workspaceMemberInvitationIds: ["pending-invite"],
      getFilteredWorkspaceMemberIds: () => [],
      getSearchedWorkspaceInvitationIds: () => ["pending-invite"],
    },
  }),
}));
vi.mock("@/hooks/store/user", () => ({
  useUserPermissions: () => ({
    allowPermissions: (roles: number[]) => roles.includes(mocks.role),
    workspaceInfoBySlug: () => ({ role: mocks.role }),
  }),
}));
vi.mock("@plane/blocks/toast", () => ({ setToast: mocks.toast }));
vi.mock("swr", () => ({ default: () => ({}) }));
vi.mock("./members-list-item", () => ({ WorkspaceMembersListItem: () => null }));
vi.mock("@/components/workspace/confirm-workspace-member-remove", () => ({ ConfirmWorkspaceMemberRemove: () => null }));
vi.mock("@plane/blocks/select", async () => {
  const { createContext } = await import("react");
  return {
    Select: Object.assign(Container, { Trigger: Container }),
    SelectDropdownPlacementContext: createContext({}),
  };
});
vi.mock("@plane/i18n", async () => {
  const { default: common } = await import("../../../../../packages/i18n/src/locales/en/common.json");
  const { default: workspace } = await import("../../../../../packages/i18n/src/locales/en/workspace-settings.json");
  const { default: accessibility } = await import("../../../../../packages/i18n/src/locales/en/accessibility.json");
  const translations = { ...common, ...workspace, ...accessibility };
  return {
    useTranslation: () => ({
      t: (key: string) => {
        const value = key
          .split(".")
          .reduce<unknown>((node, part) => (node as Record<string, unknown>)?.[part], translations);
        if (typeof value !== "string") throw new Error(`Missing translation: ${key}`);
        return value;
      },
    }),
  };
});

function Container({ children, disabled }: { children: ReactNode; disabled?: boolean }) {
  return <div aria-disabled={disabled}>{children}</div>;
}

const getAnimations = Object.getOwnPropertyDescriptor(Element.prototype, "getAnimations");
beforeAll(() => {
  // oxlint-disable-next-line no-extend-native -- jsdom does not implement the Web Animations API.
  Object.defineProperty(Element.prototype, "getAnimations", { configurable: true, value: () => [] });
});
afterAll(() => {
  // oxlint-disable-next-line no-extend-native -- Restore the original descriptor after the menu tests.
  if (getAnimations) Object.defineProperty(Element.prototype, "getAnimations", getAnimations);
  else Reflect.deleteProperty(Element.prototype, "getAnimations");
});

beforeEach(() => {
  mocks.role = 20;
  mocks.resend.mockReset().mockResolvedValue(undefined);
  mocks.toast.mockReset();
  mocks.invitation = {
    id: "pending-invite",
    email: "invitee@example.invalid",
    role: 15,
    accepted: false,
    responded_at: null,
    token: "existing-token",
    message: "",
    invite_link: "/workspace-invitations/?token=existing-token",
    workspace: { id: "workspace-id", slug: "test-workspace", name: "Test workspace", logo_url: "" },
  };
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function openMenu() {
  const user = userEvent.setup();
  render(<WorkspaceInvitationsListItem invitationId="pending-invite" />);
  await user.click(screen.getByRole("button", { name: "More actions" }));
  await screen.findByRole("menu");
  return user;
}

describe("Workspace invitation resend", () => {
  it("queues the existing invite and reports queued delivery", async () => {
    const user = await openMenu();
    await user.click(screen.getByRole("menuitem", { name: "Resend invitation" }));
    expect(mocks.resend).toHaveBeenCalledExactlyOnceWith("test-workspace", "pending-invite");
    await waitFor(() =>
      expect(mocks.toast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "success",
          title: "Success!",
          message: "Invitation queued for delivery.",
        })
      )
    );
  });

  it("allows members to resend without exposing admin actions", async () => {
    mocks.role = 15;
    await openMenu();
    expect(screen.getByRole("menuitem", { name: "Resend invitation" })).toBeDefined();
    expect(screen.queryByRole("menuitem", { name: "Copy link" })).toBeNull();
    expect(screen.queryByRole("menuitem", { name: "Remove" })).toBeNull();
    expect(screen.getByText("Member").closest("[aria-disabled]")?.getAttribute("aria-disabled")).toBe("true");
  });

  it("renders pending invitations in the members list for a workspace member", async () => {
    mocks.role = 15;
    const user = userEvent.setup();
    render(<WorkspaceMembersList searchQuery="" canViewInvitations />);
    expect(screen.getByText("invitee@example.invalid")).toBeDefined();
    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "Resend invitation" }));
    expect(mocks.resend).toHaveBeenCalledExactlyOnceWith("test-workspace", "pending-invite");
  });

  it("keeps pending invitations hidden without access to invitations", () => {
    render(<WorkspaceMembersList searchQuery="" canViewInvitations={false} />);
    expect(screen.queryByText("invitee@example.invalid")).toBeNull();
  });

  it.each([5, 15])("hides the action from role %s for an admin invitation", (role) => {
    mocks.role = role;
    mocks.invitation!.role = 20;
    render(<WorkspaceInvitationsListItem invitationId="pending-invite" />);
    expect(screen.queryByRole("button", { name: "More actions" })).toBeNull();
  });

  it.each(["accepted", "declined"])("does not resend a %s invitation", async (state) => {
    mocks.invitation!.accepted = state === "accepted";
    mocks.invitation!.responded_at = state === "declined" ? "2026-10-14T12:00:00Z" : null;
    await openMenu();
    expect(screen.queryByRole("menuitem", { name: "Resend invitation" })).toBeNull();
    expect(screen.getByRole("menuitem", { name: "Copy link" })).toBeDefined();
    expect(screen.getByRole("menuitem", { name: "Remove" })).toBeDefined();
  });

  it("blocks repeat clicks while the request is pending", async () => {
    let finish!: () => void;
    mocks.resend.mockReturnValueOnce(
      new Promise<void>((resolve) => {
        finish = resolve;
      })
    );
    const user = await openMenu();
    await user.click(screen.getByRole("menuitem", { name: "Resend invitation" }));
    const trigger = screen.getByRole("button", { name: "Resending invitation…" });
    expect(trigger.getAttribute("aria-disabled")).toBe("true");
    expect(trigger.getAttribute("aria-busy")).toBe("true");
    await user.click(trigger);
    expect(mocks.resend).toHaveBeenCalledTimes(1);
    await act(async () => finish());
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "More actions" }).getAttribute("aria-disabled")).not.toBe("true")
    );
  });

  it.each([undefined, { error: "Please wait a minute before resending this invitation" }])(
    "shows failures and lets the user try again: %j",
    async (error) => {
      mocks.resend.mockRejectedValueOnce(error);
      const user = await openMenu();
      await user.click(screen.getByRole("menuitem", { name: "Resend invitation" }));
      await waitFor(() =>
        expect(mocks.toast).toHaveBeenCalledWith(
          expect.objectContaining({
            type: "error",
            title: "Error",
            message: error?.error ?? "Unable to resend the invitation. Please try again.",
          })
        )
      );
      await user.click(screen.getByRole("button", { name: "More actions" }));
      await user.click(await screen.findByRole("menuitem", { name: "Resend invitation" }));
      expect(mocks.resend).toHaveBeenCalledTimes(2);
    }
  );

  it("can resend using the keyboard", async () => {
    const user = await openMenu();
    await user.keyboard("{Home}{Enter}");
    await waitFor(() => expect(mocks.resend).toHaveBeenCalledTimes(1));
  });

  it("renders nothing when the invitation was removed", () => {
    mocks.invitation = undefined;
    const { container } = render(<WorkspaceInvitationsListItem invitationId="pending-invite" />);
    expect(container.textContent).toBe("");
  });
});
