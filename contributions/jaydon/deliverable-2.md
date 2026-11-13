# Jaydon Devictoria

I picked three files in Plane's work item activity panel because they work together to refresh comments and activity and show them in the timeline.

Changeability

I used Oxlint to count decision paths before and after the refactor, starting from commit ed2da05. Fewer paths make the code easier to follow when making changes.

- root.tsx: I moved repeated refresh error handling into one function and reused the sort and filter defaults. Complexity went from 17 to 15.
- activity-comment-root.tsx: I calculated each row's position once and only looked up comments for comment rows. Complexity went from 7 to 5.
- activity-list.tsx: I replaced a long switch with a lookup by activity field and kept support for older entries. Complexity went from 23 to 7.

Testability

I counted the automated activity tests to see how much could be checked without opening Plane. I added 14 tests for activity types and timeline rendering, bringing the count from 8 to 22. I updated the test config so it can find the shared utilities.

Stability

I ran the same 27 web tests before and after the refactor to check for changes in existing behavior. All 27 passed both times. Run them with pnpm --filter web test. I checked the activity panel in a local browser. Comments and state changes showed together, sorting changed their order, and the Comments filter hid comments while keeping state changes visible.

Documentation

I added these notes to document the changes and how to run the tests. All three code tasks were 100% complete on November 11, 2026.

[Commit c898daa](https://github.com/WSU-CptS-481-Fall-2026/plane-zzvj/commit/c898daa22c6e4d78f06e86e13d409d18e4d9201e) (Refactor work item activity) contains the three changes and their tests.
