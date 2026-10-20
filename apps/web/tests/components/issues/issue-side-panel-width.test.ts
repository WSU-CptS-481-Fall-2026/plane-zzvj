import { describe, expect, it } from "vitest";
import { SIDE_PEEK_DESKTOP_WIDTH_CLASS } from "@/components/issues/peek-overview/layout";

describe("Issue side panel width", () => {
  // Keep the side-peek compact on desktop while retaining the full-width mobile layout.
  it("uses one-third of the desktop width", () => {
    expect(SIDE_PEEK_DESKTOP_WIDTH_CLASS).toBe("md:w-1/3");
  });
});
