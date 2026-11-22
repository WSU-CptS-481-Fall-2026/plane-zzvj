# Web component tests

Run the web application component tests from the project root with:

```bash
pnpm --filter web test
```

After syncing workspace dependencies with `pnpm install`.

Tests use the Vitest framework in `apps/web/tests/`, and can also be run with

```bash
./apps/web/node_modules/.bin/vitest run --config apps/web/vitest.config.ts
```

The UserMenuRoot test checks that the avatar menu has only one settings entry, and not the duplicate preferences and settings entries.

## Work Items analytics chart tests

`components/analytics/work-items/priority-chart-utils.test.ts` tests the pure
bar-series builder used by the Work Items analytics chart. It covers the
loading/no-data case, basic priority coloring, stacked series and rounded stack
ends, and unsupported chart models. Run only these tests from the repository
root with:

```bash
pnpm --filter web exec vitest run tests/components/analytics/work-items/priority-chart-utils.test.ts
```

The bar-series builder lives in
`apps/web/core/components/analytics/work-items/utils.ts`; keeping this logic
outside the React component allows the chart rules to be tested without
mounting the full application or calling the analytics API.

`components/analytics/work-items/workitems-insight-table-utils.test.ts` checks
the assignee avatar presentation used by the Work Items insight table: avatar
image, name initial, and placeholder states. Run it from the repository root
with:

```bash
pnpm --filter web exec vitest run tests/components/analytics/work-items/workitems-insight-table-utils.test.ts
```

`components/analytics/data-table-utils.test.ts` checks how the shared insight
table finds the first search column, reads its filter, updates that filter, and
handles a table without a searchable header. Run it from the repository root
with:

```bash
pnpm --filter web exec vitest run tests/components/analytics/data-table-utils.test.ts
```
