/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NotificationTimestamp } from "./timestamp";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-13T19:30:00Z"));
  // jsdom has no layout; the real tooltip only needs the observer lifecycle here.
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
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("NotificationTimestamp", () => {
  it("keeps relative time and reveals the exact local instant on hover without emitting a click", async () => {
    const user = userEvent.setup();
    const onRowClick = vi.fn();
    const { container } = render(<NotificationTimestamp createdAt="2026-10-13T01:30:00Z" />);
    container.addEventListener("click", onRowClick);
    const timestamp = screen.getByText("about 18 hours ago");
    expect(timestamp.getAttribute("datetime")).toBe("2026-10-13T01:30:00.000Z");
    expect(screen.queryByRole("tooltip")).toBeNull();
    await user.hover(timestamp);
    expect((await screen.findByRole("tooltip")).textContent).toBe("Oct 12, 2026, 18:30");
    expect(onRowClick).not.toHaveBeenCalled();
  });

  it("opens on keyboard focus, describes the timestamp, and dismisses with Escape", async () => {
    const user = userEvent.setup();
    const onRowClick = vi.fn();
    const { container } = render(<NotificationTimestamp createdAt="2026-10-13T01:30:00Z" />);
    container.addEventListener("click", onRowClick);
    const timestamp = screen.getByText("about 18 hours ago");
    await user.tab();
    expect(document.activeElement).toBe(timestamp);
    const tooltip = await screen.findByRole("tooltip");
    expect(timestamp.getAttribute("aria-describedby")).toBe(tooltip.id);
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("tooltip")).toBeNull());
    expect(onRowClick).not.toHaveBeenCalled();
  });

  it.each([
    ["2026-03-08T09:30:00Z", "Mar 08, 2026, 01:30"],
    ["2026-03-08T10:30:00Z", "Mar 08, 2026, 03:30"],
  ])("formats %s correctly across daylight saving time", async (createdAt, expected) => {
    const user = userEvent.setup();
    render(<NotificationTimestamp createdAt={createdAt} />);
    await user.tab();
    expect((await screen.findByRole("tooltip")).textContent).toBe(expected);
  });

  it.each([undefined, "", "not-a-date"])("renders no timestamp for %s", (createdAt) => {
    const { container } = render(<NotificationTimestamp createdAt={createdAt} />);
    expect(container.querySelector("time")).toBeNull();
    expect(screen.queryByRole("tooltip")).toBeNull();
  });
});
