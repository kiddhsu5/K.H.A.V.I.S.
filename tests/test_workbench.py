"""Unit tests for K.H.A.V.I.S. Unified Web Workbench (web/workbench.py).

Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import io
import json

from scripts.status_server import Handler
from web.workbench import (
    get_agent_fleet_status,
    list_deliverable_artifacts,
    read_artifact_content,
    render_workbench_html,
)


def test_render_workbench_html() -> None:
    html_content = render_workbench_html()
    assert "<!DOCTYPE html>" in html_content
    assert "K.H.A.V.I.S." in html_content
    assert "Workbench" in html_content
    assert "Claude Code" in html_content
    assert "Codex" in html_content
    assert "Antigravity" in html_content
    assert "MiniMax Code" in html_content
    assert "zcode" in html_content
    assert "MiniMax-M3.1-Flash" in html_content
    assert "glm-5.3-flashx" in html_content
    assert "GPT GO" in html_content
    assert "model-select-claude" in html_content
    assert "model-settings-panel" in html_content


def test_get_agent_fleet_status() -> None:
    fleet = get_agent_fleet_status()
    assert len(fleet) >= 6
    ids = [a["id"] for a in fleet]
    assert "claude" in ids
    assert "codex" in ids
    assert "antigravity" in ids
    assert "minimax" in ids
    assert "zcode" in ids
    assert "khavis" in ids

    claude_node = next(a for a in fleet if a["id"] == "claude")
    assert claude_node["model"] == "MiniMax-M3.1-Flash"

    khavis_node = next(a for a in fleet if a["id"] == "khavis")
    assert khavis_node["installed"] is True
    assert khavis_node["status"] == "ready"


def test_list_deliverable_artifacts() -> None:
    artifacts = list_deliverable_artifacts()
    assert isinstance(artifacts, list)
    assert len(artifacts) > 0
    # Should find at least our stress test script or docker compose
    names = [a["name"] for a in artifacts]
    assert any("壓力測試" in n or "Docker" in n or "投影片" in n for n in names)


def test_read_artifact_content() -> None:
    # 1. Existing file
    res = read_artifact_content("docker-compose.yml")
    assert res["ok"] is True
    assert "khavis-status" in res["content"]
    assert res["filename"] == "docker-compose.yml"

    # 2. Non-existent file (blocked by whitelist)
    res_none = read_artifact_content("non_existent_file_xyz.txt")
    assert res_none["ok"] is False
    assert "not found" in res_none["error"].lower() or "access denied" in res_none["error"].lower()

    # 3. Path traversal security protection
    res_denied = read_artifact_content("../../../etc/passwd")
    assert res_denied["ok"] is False
    assert "access denied" in res_denied["error"].lower()


class DummyStatusHandler(Handler):
    def __init__(self, path: str, method: str = "GET", body: bytes = b"") -> None:
        self.path = path
        self.command = method
        self.headers = {"Content-Length": str(len(body))}
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.responses: list[tuple[int, bytes, str]] = []

    def _send(self, status: int, body: bytes, content_type: str = "text/plain; charset=utf-8") -> None:
        self.responses.append((status, body, content_type))


def test_status_server_workbench_endpoints() -> None:
    # 1. GET /workbench  (現行介面 = 選項 C 任務卡片流)
    h_wb = DummyStatusHandler("/workbench")
    h_wb.do_GET()
    assert len(h_wb.responses) == 1
    status, body, ctype = h_wb.responses[0]
    assert status == 200
    assert "text/html" in ctype
    wb_body = body.decode("utf-8")
    assert "K.H.A.V.I.S." in wb_body
    assert 'id="c-task-stream"' in wb_body

    # 1b. GET /workbench-legacy  (改版前介面，保留作為回退路徑)
    h_legacy = DummyStatusHandler("/workbench-legacy")
    h_legacy.do_GET()
    assert len(h_legacy.responses) == 1
    status, legacy_body, legacy_ctype = h_legacy.responses[0]
    assert status == 200
    assert "text/html" in legacy_ctype
    assert "Workbench" in legacy_body.decode("utf-8")

    # 2. GET /api/workbench/artifacts
    h_art = DummyStatusHandler("/api/workbench/artifacts")
    h_art.do_GET()
    assert len(h_art.responses) == 1
    status, body, ctype = h_art.responses[0]
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["ok"] is True
    assert isinstance(data["artifacts"], list)

    # 3. GET /api/workbench/agents
    h_ag = DummyStatusHandler("/api/workbench/agents")
    h_ag.do_GET()
    assert len(h_ag.responses) == 1
    status, body, ctype = h_ag.responses[0]
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["ok"] is True
    assert len(data["agents"]) >= 6

    # 4. POST /api/workbench/dispatch with empty prompt -> 400
    h_post_empty = DummyStatusHandler("/api/workbench/dispatch", method="POST", body=b'{"prompt":""}')
    h_post_empty.do_POST()
    assert len(h_post_empty.responses) == 1
    status, body, _ = h_post_empty.responses[0]
    assert status == 400

    # 5. POST /api/workbench/dispatch with valid prompt and mocked dispatch
    from unittest.mock import AsyncMock, patch

    from bot.models import BackendResult, DispatchEnvelope, DispatchReport

    mock_report = DispatchReport(
        envelope=DispatchEnvelope(chat_id=1, prompt="test prompt"),
        results=[
            BackendResult(backend="minimax", ok=True, text="Response from MiniMax", latency_ms=120)
        ],
        consensus="Response from MiniMax",
        consensus_source="minimax",
    )
    with patch("bot.dispatch.DispatchRouter.dispatch", new_callable=AsyncMock) as mock_disp:
        mock_disp.return_value = mock_report
        h_post_valid = DummyStatusHandler(
            "/api/workbench/dispatch",
            method="POST",
            body=b'{"prompt":"test prompt","agents":["minimax"]}',
        )
        h_post_valid.do_POST()
        assert len(h_post_valid.responses) == 1
        status, body, _ = h_post_valid.responses[0]
        assert status == 200
        res_data = json.loads(body.decode("utf-8"))
        assert res_data["ok"] is True
        assert len(res_data["results"]) == 1
        assert res_data["results"][0]["backend"] == "minimax"

    # 6. GET & POST /api/workbench/models (adjustable model settings)
    h_mod_get = DummyStatusHandler("/api/workbench/models")
    h_mod_get.do_GET()
    assert h_mod_get.responses[0][0] == 200
    mod_data = json.loads(h_mod_get.responses[0][1].decode("utf-8"))
    assert mod_data["ok"] is True
    assert "claude" in mod_data["models"]

    h_mod_post = DummyStatusHandler(
        "/api/workbench/models",
        method="POST",
        body=b'{"models":{"claude":"glm-5.3-flashx","antigravity":"antigravity-flash"}}',
    )
    h_mod_post.do_POST()
    assert h_mod_post.responses[0][0] == 200
    mod_updated = json.loads(h_mod_post.responses[0][1].decode("utf-8"))
    assert mod_updated["models"]["claude"] == "glm-5.3-flashx"
    assert mod_updated["models"]["antigravity"] == "antigravity-flash"

    # Restore defaults via reset=True
    h_mod_reset = DummyStatusHandler(
        "/api/workbench/models",
        method="POST",
        body=b'{"reset":true}',
    )
    h_mod_reset.do_POST()
    assert h_mod_reset.responses[0][0] == 200
    mod_reset = json.loads(h_mod_reset.responses[0][1].decode("utf-8"))
    assert mod_reset["models"]["claude"] == "MiniMax-M3.1-Flash"
    assert mod_reset["models"]["antigravity"] == "antigravity-pro"


def test_workspace_and_worktree_endpoints() -> None:
    # 1. GET /api/workbench/workspace
    h_ws_get = DummyStatusHandler("/api/workbench/workspace")
    h_ws_get.do_GET()
    assert h_ws_get.responses[0][0] == 200
    ws_data = json.loads(h_ws_get.responses[0][1].decode("utf-8"))
    assert ws_data["ok"] is True
    assert "shared_dir" in ws_data
    assert ws_data["isolation_mode"] in ("shared", "worktree")

    # 2. Switch isolation_mode to worktree and back to shared
    h_ws_wt = DummyStatusHandler(
        "/api/workbench/workspace",
        method="POST",
        body=b'{"isolation_mode":"worktree","active_project":"shared-app"}',
    )
    h_ws_wt.do_POST()
    assert h_ws_wt.responses[0][0] == 200
    wt_data = json.loads(h_ws_wt.responses[0][1].decode("utf-8"))
    assert wt_data["isolation_mode"] == "worktree"

    import time

    from core.workspace_manager import merge_worktree_to_shared, prepare_agent_cwd

    wt_dir = prepare_agent_cwd("claude", isolation_mode="worktree", project_name="shared-app")
    (wt_dir / "hello_agent.txt").write_text(
        f"created in claude worktree at {time.time()}\n", encoding="utf-8"
    )

    merge_res = merge_worktree_to_shared("claude", project_name="shared-app", auto_commit=True)
    assert merge_res["ok"] is True
    assert "hello_agent.txt" in merge_res["copied_files"]

    # Switch back to shared mode
    h_ws_shared = DummyStatusHandler(
        "/api/workbench/workspace",
        method="POST",
        body=b'{"isolation_mode":"shared"}',
    )
    h_ws_shared.do_POST()
    assert json.loads(h_ws_shared.responses[0][1].decode("utf-8"))["isolation_mode"] == "shared"


def test_custom_agent_registration_and_execution() -> None:
    import asyncio

    from bot.backends.custom import CustomAgentBackend
    from bot.models import DispatchEnvelope
    from core.workspace_manager import prepare_agent_cwd

    # 1. Register a custom CLI agent using /bin/echo
    reg_body = json.dumps(
        {
            "id": "echo_agent",
            "name": "Echo Test Agent",
            "binary": "/bin/echo",
            "args_template": '["CustomAgentExecuted:", "{model}", "{prompt}"]',
            "default_model": "echo-v1",
            "options": ["echo-v1", "echo-v2"],
            "plan": "Self-Hosted CLI",
        }
    ).encode("utf-8")
    h_reg = DummyStatusHandler("/api/workbench/agents/custom", method="POST", body=reg_body)
    h_reg.do_POST()
    assert h_reg.responses[0][0] == 200
    reg_data = json.loads(h_reg.responses[0][1].decode("utf-8"))
    assert reg_data["ok"] is True
    assert reg_data["agent"]["id"] == "echo_agent"

    # 2. Verify custom agent appears in fleet and models config
    fleet = get_agent_fleet_status()
    assert any(a["id"] == "echo_agent" and a.get("custom") is True for a in fleet)

    # 3. Execute CustomAgentBackend inside shared workspace directory
    shared_cwd = prepare_agent_cwd("echo_agent", isolation_mode="shared", project_name="shared-app")
    backend = CustomAgentBackend(reg_data["agent"], model="echo-v2", cwd=str(shared_cwd))
    res = asyncio.run(backend.run(DispatchEnvelope(chat_id=1, prompt="hello workspace")))
    assert res.ok is True
    assert "CustomAgentExecuted:" in res.text
    assert "echo-v2" in res.text
    assert "hello workspace" in res.text

    # 4. Delete custom agent
    del_body = json.dumps({"action": "delete", "id": "echo_agent"}).encode("utf-8")
    h_del = DummyStatusHandler("/api/workbench/agents/custom", method="POST", body=del_body)
    h_del.do_POST()
    assert h_del.responses[0][0] == 200
    del_data = json.loads(h_del.responses[0][1].decode("utf-8"))
    assert del_data["deleted"] is True


def test_setup_wizard_endpoint() -> None:
    h_setup = DummyStatusHandler("/api/workbench/setup")
    h_setup.do_GET()
    assert h_setup.responses[0][0] == 200
    setup_data = json.loads(h_setup.responses[0][1].decode("utf-8"))
    assert setup_data["ok"] is True
    assert "providers" in setup_data
    assert "cli_tools" in setup_data
    assert "deploy_commands" in setup_data


def test_collaborative_orchestrator_relay_and_next_actions() -> None:
    from unittest.mock import AsyncMock, patch

    from bot.models import BackendResult, DispatchEnvelope, DispatchReport

    call_idx = 0

    async def fake_dispatch(envelope: DispatchEnvelope) -> DispatchReport:
        nonlocal call_idx
        call_idx += 1
        target = (envelope.only or ["antigravity"])[0]
        return DispatchReport(
            envelope=envelope,
            results=[
                BackendResult(
                    backend=target,
                    ok=True,
                    text=f"Step {call_idx} executed by {target}",
                    latency_ms=80,
                )
            ],
            consensus=f"Step {call_idx} executed by {target}",
            consensus_source=target,
        )

    with patch("bot.dispatch.DispatchRouter.dispatch", new_callable=AsyncMock) as mock_disp:
        mock_disp.side_effect = fake_dispatch
        body = json.dumps(
            {
                "prompt": "Build and verify health script",
                "agents": ["antigravity", "codex"],
                "collab_mode": "relay",
                "previous_context": {
                    "prompt": "Initial check",
                    "consensus": "Tailscale is active",
                },
            }
        ).encode("utf-8")
        h_relay = DummyStatusHandler("/api/workbench/dispatch", method="POST", body=body)
        h_relay.do_POST()
        assert h_relay.responses[0][0] == 200
        data = json.loads(h_relay.responses[0][1].decode("utf-8"))
        assert data["ok"] is True
        assert data["collab_mode"] == "relay"
        assert len(data["results"]) == 2
        assert len(data["collaboration_steps"]) == 2
        assert len(data["next_actions"]) >= 2
        assert "Step 2 executed by codex" in data["consensus"]


