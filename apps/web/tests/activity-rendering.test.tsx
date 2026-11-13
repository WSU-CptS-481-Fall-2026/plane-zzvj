import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EActivityFilterType, E_SORT_ORDER } from "@plane/constants";
import type { TCommentsOperations, TIssueActivityComment } from "@plane/types";
import { IssueActivityCommentRoot } from "@/components/issues/issue-detail/issue-activity/activity-comment-root";
import { IssueActivityItem } from "@/components/issues/issue-detail/issue-activity/activity/activity-list";

const store = vi.hoisted(() => ({
  getActivityById: vi.fn(),
  getActivityAndCommentsByIssueId: vi.fn(),
  getCommentById: vi.fn(),
}));

vi.mock("@/hooks/store/use-issue-detail", () => ({
  useIssueDetail: () => ({ activity: store, comment: store }),
}));
vi.mock("@/components/relations", () => ({
  useTimeLineRelationOptions: () => ({ relates_to: {} }),
}));
vi.mock("@plane/utils", () => ({
  getValidKeysFromObject: (value: Record<string, unknown>) => Object.keys(value).filter((key) => value[key]),
}));
vi.mock("@/components/comments/card/root", () => ({
  CommentCard: ({ comment, ends }: { comment: { id: string }; ends?: string }) => (
    <div data-testid={comment.id} data-end={ends}>
      Comment
    </div>
  ),
}));
vi.mock("@/components/issues/issue-detail/issue-activity/loader", () => ({
  IssueActivityLoader: () => <div>Loading activity</div>,
}));
vi.mock("@/components/issues/issue-detail/issue-activity/activity/actions", () => {
  const names = [
    "Default",
    "Name",
    "Description",
    "State",
    "Assignee",
    "Priority",
    "Estimate",
    "Parent",
    "Relation",
    "StartDate",
    "TargetDate",
    "Cycle",
    "Module",
    "Label",
    "Link",
    "Attachment",
    "ArchivedAt",
    "Inbox",
  ];

  return Object.fromEntries(
    names.map((name) => [
      `Issue${name}Activity`,
      ({ activityId, ends, showIssue }: { activityId: string; ends?: string; showIssue?: boolean }) =>
        store.getActivityById(activityId) ? (
          <div data-testid={activityId} data-end={ends} data-show-issue={showIssue}>
            {name}
          </div>
        ) : null,
    ])
  );
});

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

describe("Activity entry rendering", () => {
  it.each([
    [null, "Default"],
    ["state", "State"],
    ["relates_to", "Relation"],
    ["estimate_point", "Estimate"],
    ["estimate_points", "Estimate"],
    ["estimate_categories", "Estimate"],
    ["intake", "Inbox"],
    ["inbox", "Inbox"],
  ])("renders %s with the %s entry", (field, name) => {
    store.getActivityById.mockReturnValue({ field });
    render(<IssueActivityItem activityId="entry" ends="top" />);
    const entry = screen.getByTestId("entry");
    expect(entry.textContent).toBe(name);
    expect(entry.getAttribute("data-end")).toBe("top");
    expect(entry.getAttribute("data-show-issue")).toBe(name === "State" || name === "Estimate" ? "false" : null);
  });

  it.each(["unknown_field", "constructor", "__proto__"])("ignores unsupported field %s", (field) => {
    store.getActivityById.mockReturnValue({ field });
    const { container } = render(<IssueActivityItem activityId="entry" ends={undefined} />);
    expect(container.textContent).toBe("");
  });

  it("renders nothing when the activity is missing", () => {
    const { container } = render(<IssueActivityItem activityId="entry" ends={undefined} />);
    expect(container.textContent).toBe("");
  });
});

describe("Activity timeline", () => {
  const renderTimeline = () =>
    render(
      <IssueActivityCommentRoot
        workspaceSlug="workspace"
        projectId="project"
        issueId="work-item"
        isIntakeIssue={false}
        selectedFilters={[EActivityFilterType.COMMENT, EActivityFilterType.STATE]}
        activityOperations={{} as TCommentsOperations}
        sortOrder={E_SORT_ORDER.ASC}
      />
    );

  it("keeps the first and last markers across mixed activity and comment rows", () => {
    const entries = [
      { id: "first", activity_type: "COMMENT" },
      { id: "middle", activity_type: EActivityFilterType.STATE },
      { id: "last", activity_type: "COMMENT" },
    ] as TIssueActivityComment[];
    store.getActivityAndCommentsByIssueId.mockReturnValue(entries);
    store.getActivityById.mockReturnValue({ field: "state" });
    store.getCommentById.mockImplementation((id: string) => ({ id }));

    renderTimeline();

    expect(screen.getByTestId("first").getAttribute("data-end")).toBe("top");
    expect(screen.getByTestId("middle").getAttribute("data-end")).toBeNull();
    expect(screen.getByTestId("last").getAttribute("data-end")).toBe("bottom");
  });

  it("uses the first marker for a single row", () => {
    store.getActivityAndCommentsByIssueId.mockReturnValue([{ id: "entry", activity_type: "COMMENT" }]);
    store.getCommentById.mockReturnValue({ id: "entry" });
    renderTimeline();
    expect(screen.getByTestId("entry").getAttribute("data-end")).toBe("top");
  });
});
