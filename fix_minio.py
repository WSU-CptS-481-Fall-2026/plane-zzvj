# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Check Plane's local MinIO and restart it if needed to fix issue 9396: cannot create project.
# If Plane says **"Failed to upload cover image"** when you create a project, MinIO may not be responding.
# MinIO stores uploaded files for Plane. This tool checks whether your computer can reach MinIO. 
# If it cannot, this file will restart it.
import argparse
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def run(command, cwd):
    try:
        return subprocess.run(command, cwd=str(cwd), capture_output=True, text=True,
                              timeout=90, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Cannot execute {command[0]}: {exc}") from exc


def health_check(url):
    try:
        # Ignore system HTTP proxies for the loopback health check.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url, timeout=5) as response:
            return response.status == 200, f"HTTP {response.status}"
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        return False, str(exc)


def discover_health_url(base, project, service, container_port):
    """Find the Windows port that Docker uses for MinIO."""
    result = run(base + ["port", service, str(container_port)], project)
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError("MinIO's API port not published to the host. "
                         "Use --health-url if your setup exposes a custom health endpoint. "
                         "No restart performed.")
    first_line = result.stdout.strip().splitlines()[0].strip()
    try:
        host_port = int(first_line.rsplit(":", 1)[1])
        if not 1 <= host_port <= 65535:
            raise ValueError("out of range")
    except (IndexError, ValueError) as exc:
        raise ValueError(f"Could not read MinIO port: {first_line!r}") from exc
    return f"http://127.0.0.1:{host_port}/minio/health/live"


def main():
    parser = argparse.ArgumentParser(description="Check MinIO, restart it if not working")
    parser.add_argument("--project-dir", type=Path, default=Path.cwd(), help="Plane folder (default: this folder)")
    parser.add_argument("--compose-file", default="docker-compose-local.yml")
    parser.add_argument("--service", default="plane-minio", help="MinIO service name")
    parser.add_argument("--container-port", type=int, default=9000, help="MinIO port inside Docker")
    parser.add_argument("--health-url", help="Use a different MinIO health URL")
    parser.add_argument("--yes", action="store_true", help="Restart without asking first")
    args = parser.parse_args()

    project = args.project_dir.expanduser().resolve()
    compose_path = project / args.compose_file
    if not compose_path.is_file():
        print(f"Cannot find the Docker Compose file: {compose_path}")
        return 1
    base = ["docker", "compose", "-f", args.compose_file]
    try:
        version = run(["docker", "compose", "version"], project)
        if version.returncode != 0:
            print("Docker Compose not available:", version.stderr or version.stdout)
            return 1
        services = run(base + ["config", "--services"], project)
        if services.returncode != 0 or args.service not in services.stdout.splitlines():
            print(f"Cannot find MinIO service {args.service!r}.")
            return 1
        health_url = args.health_url or discover_health_url(base, project, args.service, args.container_port)
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Checking MinIO: {health_url}")
    healthy, detail = health_check(health_url)
    print(f"MinIO check: {detail}")
    if healthy:
        print("MinIO is working. So no restart needed.")
        return 0

    if not args.yes:
        try:
            consent = input(f"MinIO not responding. Restart? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 0
        if consent not in ("y", "yes"):
            print("Cancelled. No changes made.")
            return 0
    try:
        result = run(base + ["restart", args.service], project)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1
    if result.returncode != 0:
        print("Could not restart MinIO:", result.stderr or result.stdout)
        return 1

    for attempt in range(10):
        healthy, detail = health_check(health_url)
        if healthy:
            print(f"MinIO working again ({detail}). Try creating your project again.")
            return 0
        if attempt < 9:
            time.sleep(3)
    print(f"MinIO still not responding: {detail}")
    print("Try a different fix.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
