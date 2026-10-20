# Unit tests for the host-side MinIO.
import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "fix_minio.py"
spec = importlib.util.spec_from_file_location("fix_minio", SCRIPT)
fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix)


def result(stdout="", status=0, stderr=""):
    return subprocess.CompletedProcess([], status, stdout, stderr)


@pytest.fixture
def project(tmp_path):
    (tmp_path / "docker-compose-local.yml").write_text(
        "services:\n  plane-minio:\n    image: minio/minio\n", encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def call_script(monkeypatch, project):
    def call(*args):
        monkeypatch.setattr(sys, "argv", ["fix_minio.py", "--project-dir", str(project), *args])
        return fix.main()
    return call


@pytest.mark.unit
class TestFixMinio:

    def test_missing_published_port(self, project):
        with patch.object(fix, "run", return_value=result(status=1)):
            with pytest.raises(ValueError, match="not published"):
                fix.discover_health_url(["docker", "compose"], project, "plane-minio", 9000)

    def test_healthy_minio_does_not_restart(self, call_script):
        commands = [result("Compose v2"), result("plane-minio\n"), result("0.0.0.0:19000\n")]
        with patch.object(fix, "run", side_effect=commands) as runner, \
             patch.object(fix, "health_check", return_value=(True, "HTTP 200")) as health:
            assert call_script("--yes") == 0
        assert runner.call_count == 3
        health.assert_called_once_with("http://127.0.0.1:19000/minio/health/live")

    def test_restarts_when_connection_fails(self, call_script):
        commands = [result("Compose v2"), result("plane-minio\n"),
                    result("0.0.0.0:19000\n"), result("restarted")]
        with patch.object(fix, "run", side_effect=commands) as runner, \
             patch.object(fix, "health_check", side_effect=[(False, "reset"), (True, "HTTP 200")]):
            assert call_script("--yes") == 0
        assert runner.call_args_list[-1].args[0] == [
            "docker", "compose", "-f", "docker-compose-local.yml", "restart", "plane-minio"
        ]

    def test_user_can_cancel(self, call_script, monkeypatch):
        commands = [result("Compose v2"), result("plane-minio\n"), result("0.0.0.0:19000\n")]
        monkeypatch.setattr("builtins.input", lambda prompt: "n")
        with patch.object(fix, "run", side_effect=commands) as runner, \
             patch.object(fix, "health_check", return_value=(False, "reset")):
            assert call_script() == 0
        assert runner.call_count == 3

    def test_missing_port_does_not_restart(self, call_script):
        with patch.object(fix, "run", side_effect=[result("Compose v2"), result("plane-minio\n"), result(status=1)]) as runner:
            assert call_script("--yes") == 1
        assert runner.call_count == 3

    def test_restart_command_failure(self, call_script):
        commands = [result("Compose v2"), result("plane-minio\n"),
                    result("0.0.0.0:19000\n"), result(status=1, stderr="failed")]
        with patch.object(fix, "run", side_effect=commands), \
             patch.object(fix, "health_check", return_value=(False, "reset")):
            assert call_script("--yes") == 1
