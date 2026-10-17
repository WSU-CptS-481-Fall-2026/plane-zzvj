# Jaydon's Deliverable 1 changes

Requests: 7907, 8480 and 7447. Base: team preview commit `c7a5afee6afd15f16038ebda1ec1489ebd8af67d`.

Each request folder explains its change and tests. Web tests are in `apps/web/tests`. The Docker test is in `7907/docker-context.test.mjs`.

## Apply the patches

Use a clean checkout of the base. Copy the three files from `patches` into a folder beside that checkout named `jaydon-patches`. From the checkout's root, run:

```powershell
git apply --check ../jaydon-patches/7907.patch
git apply ../jaydon-patches/7907.patch
git apply --check ../jaydon-patches/8480.patch
git apply ../jaydon-patches/8480.patch
git apply --check ../jaydon-patches/7447.patch
git apply ../jaydon-patches/7447.patch
```

Apply 8480 before 7447 because it adds the web test setup. Check for conflicts if the team branch has newer changes.

## Run the checks

```powershell
pnpm --filter web test
pnpm --filter @plane/services test
```

See `7907/README.md` for the Docker test command.
