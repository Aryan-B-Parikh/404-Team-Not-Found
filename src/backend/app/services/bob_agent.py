"""IBM Bob provider — the app delegates to the real Bob agent.

Bob is load-bearing: the agent receives the operational question, discovers the
project PortPulse AI MCP server, calls engine tools, and writes the final answer.
The deterministic engine-grounded path is only a failure mode.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from ..config import get_settings

NO_BOB_ENV = "PORTFLOW_NO_BOB_AGENT"

BOB_OPERATIONAL_RULES = """You are the IBM Bob operations agent for PortPulse AI.
This is a decision-support application, not a generic chatbot.

Rules:
1. For every operational question, use the PortPulse AI MCP tools before answering.
2. Never invent or estimate a number when a tool can return it.
3. For forecast questions use forecast_congestion and, when useful, rank_hotspots/detect_anomalies.
4. For berth/crane questions use optimise_berth_cranes and compare its CP-SAT result with FIFO.
5. For what-if questions use simulate_scenario with the requested disruption/productivity change.
6. For routing questions use recommend_routing and query_vessels when a vessel is named.
7. For a 72-hour operating recommendation use generate_operations_plan and get_port_overview.
8. Explain the causal chain: observed data -> model/constraint -> decision -> expected impact.
9. State provenance when relevant: AIS = imported NOAA AccessAIS; DEMO_AIS = synthetic simulation.
10. If a tool fails or data is unavailable, say so explicitly. Do not fabricate a replacement.
11. Prefer a small number of targeted tool calls and synthesize their results.
"""


def disabled() -> bool:
    return os.environ.get(NO_BOB_ENV) == "1"


def _cli_path() -> str | None:
    s = get_settings()
    return shutil.which(s.bob_cli) or shutil.which(f"{s.bob_cli}.cmd") or shutil.which(f"{s.bob_cli}.exe")


def _workspace_root() -> Path:
    # services/bob_agent.py -> services -> app -> backend -> src -> repository root.
    return Path(__file__).resolve().parents[4]


def available() -> bool:
    return bool(get_settings().bob_api_key) and _cli_path() is not None and not disabled()


def parse_stream(stdout: str) -> dict:
    text, chunks, actions, tool_calls, status, cost = "", [], [], 0, None, 0.0
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "tool_use" and event.get("tool_name"):
            actions.append(event["tool_name"])
        elif kind == "message" and event.get("role") == "assistant":
            content = event.get("content")
            if isinstance(content, str):
                chunks.append(content)
            elif isinstance(content, list):
                chunks.extend(str(block["text"]) for block in content
                              if isinstance(block, dict) and block.get("type") == "text" and block.get("text"))
        elif kind == "assistant":
            content = event.get("content") or event.get("text") or ""
            if isinstance(content, str) and content.strip():
                text = content.strip()
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                        text = str(block["text"]).strip()
        elif kind == "result":
            status = event.get("status")
            stats = event.get("stats") or {}
            tool_calls = int(stats.get("tool_calls") or 0)
            cost = float(stats.get("session_costs") or 0.0)
            if event.get("last_message"):
                text = str(event["last_message"]).strip()
    if not text and chunks:
        text = "".join(chunks).strip()
    return {"text": text, "actions": actions, "tool_calls": tool_calls, "status": status, "cost": cost}


def run(prompt: str, *, max_turns: int | None = None, timeout: int | None = None, retries: int = 1) -> dict:
    """Run the agent, retrying ONLY transient failures.

    Brutal-audit finding: the old loop retried any non-ok result once, including
    deterministic failures (bad prompt, missing CLI, auth) — a blunt retry that just
    repeated a failure. Policy now: a ``timeout`` may be transient, so it is retried;
    everything else fails fast and the caller falls back to the deterministic path.
    """
    last = _run_once(prompt, max_turns=max_turns, timeout=timeout)
    attempts = retries if last.get("status") == "timeout" else 0
    for _ in range(max(0, attempts)):
        last = _run_once(prompt, max_turns=max_turns, timeout=timeout)
        if last["ok"]:
            return last
    return last


def _run_once(prompt: str, *, max_turns: int | None = None, timeout: int | None = None) -> dict:
    s = get_settings()
    cli = _cli_path()
    if not s.bob_api_key or cli is None:
        return {"ok": False, "text": "", "actions": [], "tool_calls": 0, "status": None, "error": "bob unavailable", "cost": 0.0}

    workspace = _workspace_root()
    env = {**os.environ, "BOB_API_KEY": s.bob_api_key, NO_BOB_ENV: "1"}
    if s.bob_team_id:
        env["BOB_TEAM_ID"] = s.bob_team_id
    instruction = f"{BOB_OPERATIONAL_RULES}\n\nUSER REQUEST:\n{prompt}"
    argv = [cli, "run", "--trust", "--max-turns", str(max_turns or s.bob_max_turns), "--format", "stream-json", instruction]
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(workspace),
            timeout=timeout or s.bob_timeout_s,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "text": "", "actions": [], "tool_calls": 0, "status": "timeout", "error": "bob timeout", "cost": 0.0}
    except OSError as exc:
        return {"ok": False, "text": "", "actions": [], "tool_calls": 0, "status": "error", "error": str(exc), "cost": 0.0}

    parsed = parse_stream(proc.stdout or "")
    ok = parsed["status"] == "success" and bool(parsed["text"])
    if not ok:
        try:
            with open(os.path.join(tempfile.gettempdir(), "portflow-bob-last.jsonl"), "w", encoding="utf-8") as fh:
                fh.write(proc.stdout or "")
                if proc.stderr:
                    fh.write("\n---STDERR---\n" + proc.stderr)
        except OSError:
            pass
    return {**parsed, "ok": ok, "error": None if ok else (proc.stderr or "")[-300:]}
