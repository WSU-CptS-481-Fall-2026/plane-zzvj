# Request 7907

Issue: https://github.com/makeplane/plane/issues/7907

The root `.dockerignore` now uses `**/*.pyc` instead of `*.pyc` so nested Python bytecode is excluded too. This affects builds using the repository root as their context, not builds whose context is `apps/api`.

## Test

From the repository root, with Node 22 and Docker running:

```powershell
$env:REQUIRE_DOCKER = '1'
node --test contributions/jaydon/7907/docker-context.test.mjs
Remove-Item Env:REQUIRE_DOCKER
```

The test uses the real ignore file in a temporary `FROM scratch` build. It checks four excluded bytecode paths and five included files, including Python source and `.pyc.txt`. It cleans up its temporary folder and leaves project containers and volumes alone.

Without `REQUIRE_DOCKER=1`, an unavailable engine causes a skip. A skip doesn't verify the fix.

Pattern reference: https://docs.docker.com/build/concepts/context/#dockerignore-files
