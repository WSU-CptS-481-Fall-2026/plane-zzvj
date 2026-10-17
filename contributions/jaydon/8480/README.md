# Request 8480

Issue: https://github.com/makeplane/plane/issues/8480

The activity view previously loaded data on opening and after local actions. It now checks for another user's new comments and activity every 15 seconds through two independent SWR polls and the existing stores.

It also checks on focus and reconnection, pauses while hidden or offline, and stops future polls when closed. A request already running can finish for its original item. One pending history request doesn't block the other. Failed requests are logged and can retry at the next interval; `finally` clears the comment loader.

The existing `created_at__gt` queries fetch new entries and merge IDs without duplicates. Polling preserves the editor, filters and sorting. It doesn't add updates for another user's comment edits or deletions.

## Tests

From the repository root with Node 22.22 or later and the repository's pnpm version:

```powershell
pnpm install --frozen-lockfile
pnpm --filter web test tests/issue-activity-refresh.test.tsx
```

Ten tests use the real activity components, SWR and stores with fake timers. API responses and some UI controls are test doubles. They cover refreshes, drafts, duplicates, filters, visibility/connectivity, item changes, failed or pending requests, and local comment operations. Only test dependencies are added.

## Two-user check

1. Open the same work item as two different users in separate browser profiles.
2. Keep A visible with an unsent draft. Post a new comment from B. It should appear in A after the next successful refresh without reloading or losing the draft.
3. Change the state in B. Check its history entry appears in A without duplicates on later polls.
4. Clear the draft, then check filters, sorting and local comment create/edit/delete.
5. Switch A to another item and check the request IDs. Close the activity view and confirm its interval requests stop. Hidden/offline views should pause and resume when visible/online.
