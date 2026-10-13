"""Script to execute manual curl calls against the real database and record outputs (Phase 4, Task 7)."""

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def wait_for_server(url: str, timeout: float = 10.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def run_curl(cmd: list[str]) -> str:
    print(f"Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return res.stdout


def main() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["CARECAST_ENV"] = "dev"
    env["CARECAST_ENABLE_DOCS"] = "1"
    env["CARECAST_DB_PATH"] = "data/carecast.db"

    # Start uvicorn server as subprocess
    server_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "carecast.api.main:create_app",
        "--factory",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]

    print("Launching CareCast API server...")
    proc = subprocess.Popen(server_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        health_url = "http://127.0.0.1:8000/api/v1/health"
        if not wait_for_server(health_url, timeout=15.0):
            print("ERROR: Server failed to start within timeout.")
            return

        print("Server is up and responsive. Executing curl calls against endpoints...")

        calls = [
            ("E1_HEALTH", ["curl.exe", "-s", "-i", "http://127.0.0.1:8000/api/v1/health"]),
            ("E2_META", ["curl.exe", "-s", "-i", "http://127.0.0.1:8000/api/v1/meta"]),
            ("E3_SUMMARY_FLU", ["curl.exe", "-s", "-i", "http://127.0.0.1:8000/api/v1/summary?disease=flu&jurisdiction=US"]),
            ("E3_SUMMARY_COVID", ["curl.exe", "-s", "-i", "http://127.0.0.1:8000/api/v1/summary?disease=covid19&jurisdiction=US"]),
            ("E3_SUMMARY_RSV", ["curl.exe", "-s", "-i", "http://127.0.0.1:8000/api/v1/summary?disease=rsv&jurisdiction=US"]),
            ("E4_OBSERVATIONS", ["curl.exe", "-s", "-i", "http://127.0.0.1:8000/api/v1/observations?disease=flu&jurisdiction=US&from=2024-01-06&to=2024-03-30"]),
            ("E5_FORECAST_FLU", ["curl.exe", "-s", "-i", "http://127.0.0.1:8000/api/v1/forecast?disease=flu&jurisdiction=US"]),
            ("E6_EVALUATION_FLU_H1", ["curl.exe", "-s", "-i", "http://127.0.0.1:8000/api/v1/evaluation?disease=flu&jurisdiction=US&horizon=1"]),
            ("E7_EXPLAIN_FLU_H1", ["curl.exe", "-s", "-i", "http://127.0.0.1:8000/api/v1/explain?disease=flu&jurisdiction=US&horizon=1"]),
            ("E8_SCENARIO_FLU", [
                "curl.exe", "-s", "-i", "-X", "POST", "http://127.0.0.1:8000/api/v1/scenario",
                "-H", "Content-Type: application/json",
                "-d", '{"disease":"flu","jurisdiction":"US","surge_pct":20.0,"threshold":null,"capacity":{"typical_weekly_admissions":100.0,"alos_days":4.5,"staffed_beds":80.0,"patients_per_nurse":4.0}}'
            ]),
            ("ERROR_422_VALIDATION", ["curl.exe", "-s", "-i", "http://127.0.0.1:8000/api/v1/observations?disease=flu&jurisdiction=US&from=2024-05-01&to=2024-01-01"]),
            ("ERROR_413_PAYLOAD_TOO_LARGE", [
                "curl.exe", "-s", "-i", "-X", "POST", "http://127.0.0.1:8000/api/v1/scenario",
                "-H", "Content-Type: application/json",
                "-d", '{"disease":"flu","jurisdiction":"US","surge_pct":20.0,"padding":"' + ('A' * 9000) + '"}'
            ]),
        ]

        output_lines = [
            "# CareCast Phase 4 — Manual curl Output Audit Log",
            f"# Generated on: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
            "# Database: data/carecast.db (Real Ingested Data)",
            "=" * 80,
            "",
        ]

        for label, cmd in calls:
            output_lines.append(f"## {label}")
            output_lines.append(f"$ {' '.join(cmd[:6])} ...")
            res_text = run_curl(cmd)
            output_lines.append(res_text)
            output_lines.append("-" * 80)
            output_lines.append("")

        out_path = Path("reports/logs/p4-curl-endpoints.txt")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(output_lines), encoding="utf-8")
        print(f"Audit log saved to {out_path}")

    finally:
        print("Stopping uvicorn server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("Server stopped.")


if __name__ == "__main__":
    main()
