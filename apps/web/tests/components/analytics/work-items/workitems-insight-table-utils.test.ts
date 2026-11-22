import { describe, expect, it } from "vitest";
import { getAssigneeAvatarPresentation } from "@/components/analytics/work-items/workitems-insight-table.utils";

describe("getAssigneeAvatarPresentation", () => {
  it("uses the avatar image when a URL is available", () => {
    expect(getAssigneeAvatarPresentation("https://example.com/avatar.png", "Taylor Smith")).toEqual({
      kind: "avatar",
      avatarUrl: "https://example.com/avatar.png",
      displayName: "Taylor Smith",
    });
  });

  it("uses the first character when the assignee has a name but no avatar", () => {
    expect(getAssigneeAvatarPresentation(undefined, "Taylor Smith")).toEqual({
      kind: "initial",
      initial: "T",
    });
  });

  it("uses a placeholder for an empty avatar URL and missing name", () => {
    expect(getAssigneeAvatarPresentation("", undefined)).toEqual({ kind: "placeholder" });
  });
});
