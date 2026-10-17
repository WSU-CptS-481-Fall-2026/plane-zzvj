import { useState } from "react";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { SWRConfig } from "swr";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EActivityFilterType, E_SORT_ORDER, defaultActivityFilters } from "@plane/constants";
import type { TIssueActivity, TIssueComment } from "@plane/types";
import { EIssueServiceType } from "@plane/types";
import { IssueActivity } from "@/components/issues/issue-detail/issue-activity/root";
import { IssueActivityStore } from "@/store/issue/issue-details/activity.store";
import { IssueCommentStore } from "@/store/issue/issue-details/comment.store";
import type { IIssueDetail } from "@/store/issue/issue-details/root.store";
import type { CoreRootStore } from "@/store/root.store";

const backend = vi.hoisted(() => ({
  comments: vi.fn(),
  activities: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  remove: vi.fn(),
  detail: undefined as unknown,
  projectExists: true,
}));

vi.mock("@/services/issue", () => ({
  IssueCommentService: class {
    getIssueComments = backend.comments;
    createIssueComment = backend.create;
    patchIssueComment = backend.update;
    deleteIssueComment = backend.remove;
  },
  IssueActivityService: class {
    getIssueActivities = backend.activities;
  },
}));
vi.mock("@/hooks/store/use-issue-detail", () => ({ useIssueDetail: () => backend.detail }));
vi.mock("@/hooks/store/use-project", () => ({
  useProject: () => ({ getProjectById: () => (backend.projectExists ? { anchor: null } : undefined) }),
}));
vi.mock("@plane/i18n", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock("@plane/hooks", () => ({
  useLocalStorage: (_key: string, initial: unknown) => {
    const [storedValue, setValue] = useState(initial);
    return { storedValue, setValue };
  },
}));
vi.mock("@/components/issues/issue-detail/issue-activity/helper", () => ({
  useWorkItemCommentOperations: () => ({}),
}));
vi.mock("@/components/comments/comment-create", () => ({
  CommentCreate: () => <textarea aria-label="Comment draft" />,
}));
vi.mock("@/components/comments/card/root", () => ({
  CommentCard: ({ comment }: { comment: TIssueComment }) => <p>{comment.comment_html}</p>,
}));
vi.mock("@/components/issues/issue-detail/issue-activity/activity/activity-list", () => ({
  IssueActivityItem: ({ activityId }: { activityId: string }) => <p>{activityId}</p>,
}));
vi.mock("@/components/issues/issue-detail/issue-activity/loader", () => ({
  IssueActivityLoader: () => <p>Loading</p>,
}));
vi.mock("@/components/issues/issue-detail/issue-activity/sort-root", () => ({
  ActivitySortRoot: ({ toggleSort }: { toggleSort: () => void }) => <button onClick={toggleSort}>Sort</button>,
}));
vi.mock("@/components/issues/issue-detail/issue-activity/filter-root", () => ({
  ActivityFilterRoot: ({ toggleFilter }: { toggleFilter: (filter: EActivityFilterType) => void }) => (
    <button onClick={() => toggleFilter(EActivityFilterType.COMMENT)}>Toggle comments</button>
  ),
}));

let detail: IIssueDetail;
const comment = (id: string, text = id) =>
  ({
    id,
    comment_html: text,
    created_at: "2026-10-13T10:00:00Z",
    comment_reactions: [],
  }) as unknown as TIssueComment;
const activity = (id: string) =>
  ({
    id,
    field: "state",
    created_at: "2026-10-13T10:01:00Z",
  }) as unknown as TIssueActivity;
const props = { workspaceSlug: "test-workspace", projectId: "test-project", issueId: "first-item" };

beforeEach(async () => {
  vi.useFakeTimers();
  vi.clearAllMocks();
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
  backend.projectExists = true;
  backend.comments.mockResolvedValue([]);
  backend.activities.mockResolvedValue([]);
  detail = { commentReaction: { applyCommentReactions: vi.fn() } } as unknown as IIssueDetail;
  const root = { issue: { issueDetail: detail } } as unknown as CoreRootStore;
  detail.activity = new IssueActivityStore(root);
  detail.comment = new IssueCommentStore(detail, EIssueServiceType.ISSUES);
  detail.fetchActivities = (...args) => detail.activity.fetchActivities(...args);
  detail.fetchComments = (...args) => detail.comment.fetchComments(...args);
  backend.detail = detail;
  await detail.activity.fetchActivities(props.workspaceSlug, props.projectId, props.issueId);
  await detail.comment.fetchComments(props.workspaceSlug, props.projectId, props.issueId);
  backend.comments.mockClear();
  backend.activities.mockClear();
});

afterEach(() => {
  cleanup();
  window.dispatchEvent(new Event("online"));
  vi.useRealTimers();
  vi.restoreAllMocks();
});

const mount = (issueId = props.issueId) =>
  render(
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      <IssueActivity {...props} issueId={issueId} />
    </SWRConfig>
  );
const tick = async (ms = 15000) => {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
};

describe("#8480 activity refresh", () => {
  it("shows a new remote comment without reopening or reloading the view", async () => {
    mount();
    expect(screen.queryByText("Other user's comment")).toBeNull();
    backend.comments.mockResolvedValue([comment("remote", "Other user's comment")]);
    await tick();
    expect(screen.getByText("Other user's comment")).toBeTruthy();
    expect(backend.comments).toHaveBeenCalledWith("test-workspace", "test-project", "first-item", {});
  });

  it("merges activity and comments once and preserves the draft and sort/filter choices", async () => {
    mount();
    fireEvent.click(screen.getByRole("button", { name: "Sort" }));
    fireEvent.change(screen.getByLabelText("Comment draft"), { target: { value: "unsent draft" } });
    backend.comments.mockResolvedValue([comment("remote")]);
    backend.activities.mockResolvedValue([activity("remote-state-change")]);
    await tick();
    await tick();
    expect(screen.getAllByText("remote")).toHaveLength(1);
    expect(screen.getAllByText("remote-state-change")).toHaveLength(1);
    expect((screen.getByLabelText("Comment draft") as HTMLTextAreaElement).value).toBe("unsent draft");
    const items = detail.activity.getActivityAndCommentsByIssueId(props.issueId, E_SORT_ORDER.DESC)!;
    expect(items.map((item) => item.id)).toEqual(["remote-state-change", "remote"]);
    expect(backend.comments).toHaveBeenLastCalledWith("test-workspace", "test-project", "first-item", {
      created_at__gt: "2026-10-13T10:00:00Z",
    });
    expect(defaultActivityFilters).toContain(EActivityFilterType.COMMENT);
    fireEvent.click(screen.getByRole("button", { name: "Toggle comments" }));
    await tick();
    expect(screen.queryByText("remote")).toBeNull();
    expect(screen.getByText("remote-state-change")).toBeTruthy();
  });

  it("pauses in a hidden tab and stops when the view closes", async () => {
    const view = mount();
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
    await tick();
    expect(backend.comments).not.toHaveBeenCalled();
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
    await tick();
    expect(backend.comments).toHaveBeenCalledOnce();
    view.unmount();
    await tick(30000);
    expect(backend.comments).toHaveBeenCalledOnce();
  });

  it("checks on focus and reconnection and pauses while offline", async () => {
    mount();
    await tick(6000);
    window.dispatchEvent(new Event("focus"));
    await tick(1);
    expect(backend.comments).toHaveBeenCalledOnce();
    window.dispatchEvent(new Event("offline"));
    await tick(15000);
    expect(backend.comments).toHaveBeenCalledOnce();
    window.dispatchEvent(new Event("online"));
    await tick(1);
    expect(backend.comments).toHaveBeenCalledTimes(2);
  });

  it("uses the new item after switching and does not fetch without a project", async () => {
    const view = mount();
    await tick();
    view.rerender(
      <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
        <IssueActivity {...props} issueId="second-item" />
      </SWRConfig>
    );
    await tick();
    expect(backend.comments.mock.calls.filter((call) => call[2] === "first-item")).toHaveLength(1);
    expect(backend.comments.mock.calls.some((call) => call[2] === "second-item")).toBe(true);
    expect(backend.comments.mock.calls.slice(1).every((call) => call[2] === "second-item")).toBe(true);
    const callsBeforeMissingProject = backend.comments.mock.calls.length;
    view.unmount();
    backend.projectExists = false;
    mount();
    await tick();
    expect(backend.comments).toHaveBeenCalledTimes(callsBeforeMissingProject);
  });

  it("recovers at the next interval after a failed request without losing existing comments", async () => {
    backend.create.mockResolvedValue(comment("local", "Existing comment"));
    await detail.comment.createComment("test-workspace", "test-project", "first-item", {});
    const log = vi.spyOn(console, "error").mockImplementation(() => {});
    mount();
    backend.comments.mockRejectedValueOnce(new Error("Temporary network failure"));
    await tick();
    expect(screen.getByText("Existing comment")).toBeTruthy();
    expect(detail.comment.loader).toBeUndefined();
    expect(log).toHaveBeenCalledOnce();
    backend.comments.mockResolvedValue([comment("remote", "Recovered comment")]);
    await tick();
    expect(screen.getByText("Recovered comment")).toBeTruthy();
    expect(screen.getByText("Existing comment")).toBeTruthy();
  });

  it("does not overlap refreshes while a previous request is pending", async () => {
    let finish!: (comments: TIssueComment[]) => void;
    backend.comments.mockReturnValue(
      new Promise<TIssueComment[]>((resolve) => {
        finish = resolve;
      })
    );
    mount();
    await tick();
    await tick(30000);
    expect(backend.comments).toHaveBeenCalledOnce();
    await act(async () => {
      finish([comment("slow")]);
    });
    expect(screen.getByText("slow")).toBeTruthy();
    await tick();
    expect(backend.comments).toHaveBeenCalledTimes(2);
  });

  it.each(["comments", "activities"] as const)(
    "keeps the other history refreshing while %s is pending",
    async (pendingHistory) => {
      let finish!: (entries: []) => void;
      backend[pendingHistory].mockReturnValue(
        new Promise<[]>((resolve) => {
          finish = resolve;
        })
      );
      const otherHistory = pendingHistory === "comments" ? "activities" : "comments";
      const first = otherHistory === "comments" ? comment("first") : activity("first");
      const second = otherHistory === "comments" ? comment("second") : activity("second");
      backend[otherHistory].mockResolvedValueOnce([first]).mockResolvedValueOnce([second]);
      mount();
      await tick();
      expect(screen.getByText("first")).toBeTruthy();
      await tick();
      expect(screen.getByText("second")).toBeTruthy();
      expect(backend[pendingHistory]).toHaveBeenCalledOnce();
      expect(backend[otherHistory]).toHaveBeenCalledTimes(2);
      await act(async () => {
        finish([]);
      });
    }
  );

  it("keeps local comment creation, editing and deletion working", async () => {
    backend.create.mockResolvedValue(comment("local", "original"));
    await detail.comment.createComment("test-workspace", "test-project", "first-item", {});
    expect(detail.comment.getCommentById("local")?.comment_html).toBe("original");
    backend.update.mockResolvedValue({ updated_at: "2026-10-13T12:00:00Z", edited_at: "2026-10-13T12:00:00Z" });
    await detail.comment.updateComment("test-workspace", "test-project", "first-item", "local", {
      comment_html: "edited",
    });
    expect(detail.comment.getCommentById("local")?.comment_html).toBe("edited");
    backend.remove.mockResolvedValue(undefined);
    await detail.comment.removeComment("test-workspace", "test-project", "first-item", "local");
    expect(detail.comment.getCommentsByIssueId("first-item")).toEqual([]);
    expect(detail.comment.getCommentById("local")).toBeUndefined();
  });
});
