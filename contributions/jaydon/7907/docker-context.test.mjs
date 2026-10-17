import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const repo = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const engine = spawnSync("docker", ["info", "--format", "{{.ServerVersion}}"], { encoding: "utf8", timeout: 15000 });
const dockerAvailable = engine.status === 0;

test(
  "#7907 Docker excludes bytecode at every depth and keeps source files",
  {
    skip:
      !dockerAvailable && process.env.REQUIRE_DOCKER !== "1"
        ? "Docker engine unavailable; context test not run"
        : false,
  },
  () => {
    assert.ok(dockerAvailable, "Docker engine is required for this test. Start Docker Desktop first.");
    const fixture = mkdtempSync(join(tmpdir(), "plane-7907-"));
    const context = join(fixture, "context");
    const output = join(fixture, "output");
    const excluded = ["root.pyc", "one/module.pyc", "one/two/module.pyc", "one/two/__pycache__/module.cpython-312.pyc"];
    const included = ["root.py", "one/module.py", "one/two/module.py", "one/two/module.pyc.txt", "one/two/notes.txt"];
    try {
      mkdirSync(context);
      copyFileSync(join(repo, ".dockerignore"), join(context, ".dockerignore"));
      for (const path of [...excluded, ...included]) {
        const destination = join(context, path);
        mkdirSync(dirname(destination), { recursive: true });
        writeFileSync(destination, "fixture data\n");
      }
      writeFileSync(join(context, "Dockerfile"), "FROM scratch\nCOPY . /\n");
      const build = spawnSync("docker", ["build", "--output", `type=local,dest=${output}`, context], {
        encoding: "utf8",
        timeout: 120000,
      });
      assert.equal(build.status, 0, `Fixture build failed: ${build.stderr || build.error?.message}`);
      for (const path of excluded) assert.equal(existsSync(join(output, path)), false, `${path} entered the context`);
      for (const path of included)
        assert.equal(readFileSync(join(output, path), "utf8"), "fixture data\n", `${path} was excluded`);
    } finally {
      // Clean up this test's temporary folder.
      rmSync(fixture, { recursive: true, force: true });
    }
  }
);
