# Web component tests

Run the web application compoennt tests from the project root with:

```bash
pnpm --filter web test
```

After syncing workspace dependencies with `pnpm install`.

Tests use the Vitest frameowrk in `apps/web/tests/`, and can be run with

```bash
./apps/web/node_modules/.bin/vitest run --config apps/web/vitest.config.ts
```

The UserMenuRoot test checks that the avatar menu has only one settings entry, and not the duplicate preferences and settings entries.
