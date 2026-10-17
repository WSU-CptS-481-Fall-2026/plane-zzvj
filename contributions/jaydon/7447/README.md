# Request 7447

Issue: https://github.com/makeplane/plane/issues/7447

The work-items tour description removes the extra article before Plane and the unmatched either. Other descriptions, images and navigation stay the same.

## Tests

After installing workspace dependencies:

```powershell
pnpm --filter web test tests/onboarding-tour.test.tsx
```

Three tests render the tour and sidebar. They check the wording, Next, Back, sidebar selection, the create-project callback, skipping and closing. User hooks, icons and the shared Button are test doubles; the tests don't create a real server-side project.

## Upstream comparison

PR https://github.com/makeplane/plane/pull/9996 was still open when checked October 16, 2026. It makes the same grammar correction but uses `or their properties`; this patch keeps `and their properties` and adds rendered tour tests.

Apply the 8480 patch first for the web test setup.
