"""Shared Workspace & Git Worktree Manager for Multi-CLI Collaboration.

Enables all 5 CLI Agents (Claude Code, Codex, Antigravity, MiniMax Code, zcode)
to either:
1. Execute seamlessly inside a single shared project directory (`shared` mode, default),
   allowing sequential or cooperative CLI runs to read/write the same files directly.
2. Execute in isolated Git Worktrees (`worktree` mode) during parallel fan-out,
   capturing per-agent unified diffs and supporting one-click merge back into the
   shared project directory.

Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKSPACE_ROOT = PROJECT_ROOT / "workspace"
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._\-]{1,64}$")


def get_workspace_root() -> Path:
    """Return the root directory holding shared project folders."""
    custom = os.environ.get("KHAVIS_WORKSPACE_ROOT", "").strip()
    root = Path(custom).resolve() if custom else DEFAULT_WORKSPACE_ROOT.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_active_project_name() -> str:
    """Return the currently active shared project folder name."""
    name = os.environ.get("KHAVIS_ACTIVE_PROJECT", "shared-app").strip()
    if not _SAFE_NAME_RE.match(name):
        name = "shared-app"
    return name


def get_active_isolation_mode() -> str:
    """Return current default execution mode: 'shared' (default) or 'worktree'."""
    mode = os.environ.get("KHAVIS_ISOLATION_MODE", "shared").strip().lower()
    return "worktree" if mode == "worktree" else "shared"


def load_workspace_config() -> dict[str, str]:
    """Return current workspace configuration dict."""
    return {
        "active_project": get_active_project_name(),
        "isolation_mode": get_active_isolation_mode(),
    }


def _run_git(cwd: Path, args: list[str], timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )


def ensure_project_initialized(project_name: str | None = None) -> Path:
    """Ensure the shared project directory exists and is initialized as a Git repo."""
    root = get_workspace_root()
    name = (project_name or get_active_project_name()).strip()
    if not _SAFE_NAME_RE.match(name):
        raise ValueError(f"Invalid project folder name: {name!r}")

    proj_dir = (root / name).resolve()
    proj_dir.mkdir(parents=True, exist_ok=True)

    readme_path = proj_dir / "README.md"
    if not readme_path.exists():
        readme_path.write_text(
            f"# {name} (K.H.A.V.I.S. 共用專案工作區)\n\n"
            "此目錄為所有 CLI Agent (Claude Code, Codex, Antigravity, MiniMax Code, zcode) 共用的執行資料夾。\n"
            "- **共用資料夾模式 (Shared Mode)**：各 CLI 直接於此目錄讀寫檔案，無縫接力開發。\n"
            "- **Git Worktree 隔離模式 (Worktree Mode)**：並發派工時自動建立獨立分支，支援 Diff 視覺化對比與一鍵合併。\n",
            encoding="utf-8",
        )

    gitignore_path = proj_dir / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text(".worktrees/\n__pycache__/\n*.pyc\n.DS_Store\n", encoding="utf-8")

    git_dir = proj_dir / ".git"
    if not git_dir.exists():
        _run_git(proj_dir, ["init", "-b", "main"])
        _run_git(proj_dir, ["config", "user.name", "KHAVIS Workspace"])
        _run_git(proj_dir, ["config", "user.email", "workspace@khavis.local"])
        _run_git(proj_dir, ["add", "-A"])
        _run_git(proj_dir, ["commit", "-m", "chore: initialize shared project workspace"])
    else:
        head_check = _run_git(proj_dir, ["rev-parse", "--verify", "HEAD"])
        if head_check.returncode != 0:
            _run_git(proj_dir, ["config", "user.name", "KHAVIS Workspace"])
            _run_git(proj_dir, ["config", "user.email", "workspace@khavis.local"])
            _run_git(proj_dir, ["add", "-A"])
            _run_git(proj_dir, ["commit", "--allow-empty", "-m", "chore: initialize shared workspace"])

    return proj_dir


def prepare_agent_cwd(
    agent_id: str,
    isolation_mode: str | None = None,
    project_name: str | None = None,
) -> Path:
    """Return the working directory for a CLI agent execution.

    - In 'shared' mode (default): returns the shared project directory so all CLIs
      collaborate smoothly on the exact same files.
    - In 'worktree' mode: creates/resets a dedicated Git worktree under
      `<project_dir>/.worktrees/<agent_id>` on branch `khavis/<agent_id>`.
    """
    proj_dir = ensure_project_initialized(project_name)
    mode = (isolation_mode or get_active_isolation_mode()).strip().lower()
    if mode != "worktree":
        return proj_dir

    safe_agent = re.sub(r"[^A-Za-z0-9_\-]", "", agent_id) or "agent"
    wt_root = proj_dir / ".worktrees"
    wt_root.mkdir(parents=True, exist_ok=True)
    wt_dir = (wt_root / safe_agent).resolve()
    branch_name = f"khavis/{safe_agent}"

    if wt_dir.exists():
        _run_git(proj_dir, ["worktree", "remove", "--force", str(wt_dir)])
        shutil.rmtree(wt_dir, ignore_errors=True)

    _run_git(proj_dir, ["worktree", "prune"])
    res = _run_git(proj_dir, ["worktree", "add", "-B", branch_name, str(wt_dir), "HEAD"])
    if res.returncode != 0 or not wt_dir.exists():
        # Fallback to shared dir if git worktree is unavailable
        return proj_dir

    # Also copy any uncommitted files from shared dir into the worktree so it starts up-to-date
    for item in proj_dir.iterdir():
        if item.name in (".git", ".worktrees"):
            continue
        dest = wt_dir / item.name
        try:
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            elif item.is_file():
                shutil.copy2(item, dest)
        except OSError:
            pass

    return wt_dir


def collect_directory_diff(target_dir: Path) -> dict[str, Any]:
    """Collect git status, changed file list, and unified diff (including untracked files)."""
    if not target_dir.exists():
        return {"changed_files": [], "diff": "", "has_changes": False}

    status_proc = _run_git(target_dir, ["status", "--porcelain"])
    changed_files: list[dict[str, str]] = []
    untracked_paths: list[Path] = []

    for line in (status_proc.stdout or "").splitlines():
        if len(line) < 4:
            continue
        code = line[:2].strip() or "M"
        rel_path = line[3:].strip()
        if rel_path.startswith(".worktrees"):
            continue
        changed_files.append({"status": code, "path": rel_path})
        if code == "??":
            untracked_paths.append(target_dir / rel_path)

    diff_proc = _run_git(target_dir, ["diff", "HEAD", "--", ".", ":!.worktrees"])
    diff_parts: list[str] = []
    if diff_proc.stdout and diff_proc.stdout.strip():
        diff_parts.append(diff_proc.stdout.strip())

    # Append synthetic unified diff for untracked files so new files are visible in Diff viewer
    for upath in untracked_paths[:10]:
        if upath.is_file():
            try:
                rel = upath.relative_to(target_dir)
                content = upath.read_text(encoding="utf-8", errors="replace")[:4000]
                added_lines = "\n".join(f"+{ln}" for ln in content.splitlines())
                diff_parts.append(
                    f"diff --git a/{rel} b/{rel}\n"
                    f"new file mode 100644\n"
                    f"--- /dev/null\n"
                    f"+++ b/{rel}\n"
                    f"@@ -0,0 +1,{len(content.splitlines())} @@\n"
                    f"{added_lines}"
                )
            except OSError:
                pass

    full_diff = "\n\n".join(diff_parts)
    return {
        "changed_files": changed_files,
        "diff": full_diff,
        "has_changes": bool(changed_files or full_diff.strip()),
    }


def list_project_files(proj_dir: Path) -> list[dict[str, Any]]:
    """List user files inside the shared project workspace."""
    files: list[dict[str, Any]] = []
    if not proj_dir.exists():
        return files

    for p in sorted(proj_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(proj_dir)
        if any(part.startswith(".git") or part == ".worktrees" or part == "__pycache__" for part in rel.parts):
            continue
        try:
            st = p.stat()
            files.append(
                {
                    "name": p.name,
                    "rel_path": str(rel),
                    "path": str(p),
                    "size_bytes": st.st_size,
                    "size": f"{max(0.1, round(st.st_size / 1024, 1))} KB" if st.st_size >= 100 else f"{st.st_size} B",
                    "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
                }
            )
        except OSError:
            continue
    return files


def get_workspace_status(project_name: str | None = None) -> dict[str, Any]:
    """Return comprehensive state of the shared project directory and any active worktrees."""
    root = get_workspace_root()
    proj_dir = ensure_project_initialized(project_name)
    active_name = proj_dir.name

    projects = sorted(
        d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")
    )
    branch_proc = _run_git(proj_dir, ["rev-parse", "--abbrev-ref", "HEAD"])
    branch = (branch_proc.stdout or "main").strip() or "main"

    shared_diff_info = collect_directory_diff(proj_dir)
    files = list_project_files(proj_dir)

    worktrees_info: list[dict[str, Any]] = []
    wt_root = proj_dir / ".worktrees"
    if wt_root.exists():
        for wt_dir in sorted(wt_root.iterdir()):
            if not wt_dir.is_dir():
                continue
            agent_id = wt_dir.name
            wt_diff = collect_directory_diff(wt_dir)
            worktrees_info.append(
                {
                    "agent": agent_id,
                    "path": str(wt_dir),
                    "branch": f"khavis/{agent_id}",
                    "changed_files": wt_diff["changed_files"],
                    "diff": wt_diff["diff"],
                    "has_changes": wt_diff["has_changes"],
                }
            )

    return {
        "ok": True,
        "workspace_root": str(root),
        "active_project": active_name,
        "active_path": str(proj_dir),
        "shared_dir": str(proj_dir),
        "isolation_mode": get_active_isolation_mode(),
        "branch": branch,
        "projects": projects,
        "files": files,
        "changed_files": shared_diff_info["changed_files"],
        "diff": shared_diff_info["diff"],
        "has_changes": shared_diff_info["has_changes"],
        "worktrees": worktrees_info,
    }


def configure_workspace(payload: dict[str, Any]) -> dict[str, Any]:
    """Switch or create the active shared project folder, isolation mode, or merge/commit actions."""
    action = str(payload.get("action") or "").strip().lower()
    project_name = str(payload.get("project") or payload.get("active_project") or "").strip()
    isolation_mode = str(payload.get("isolation_mode") or "").strip().lower()

    if action == "merge_worktree":
        agent_id = str(payload.get("agent") or payload.get("agent_id") or "").strip()
        auto_commit = bool(payload.get("auto_commit", True))
        return merge_worktree_to_shared(agent_id, project_name=project_name or None, auto_commit=auto_commit)

    if action == "commit_shared":
        msg = str(payload.get("message") or "").strip()
        return commit_shared_workspace(message=msg, project_name=project_name or None)

    if project_name:
        if not _SAFE_NAME_RE.match(project_name):
            raise ValueError(f"Invalid project folder name: {project_name!r}")
        os.environ["KHAVIS_ACTIVE_PROJECT"] = project_name
        ensure_project_initialized(project_name)

    if isolation_mode in ("shared", "worktree"):
        os.environ["KHAVIS_ISOLATION_MODE"] = isolation_mode

    return get_workspace_status(project_name or None)


def merge_worktree_to_shared(
    agent_id: str,
    project_name: str | None = None,
    auto_commit: bool = False,
) -> dict[str, Any]:
    """Apply all modified/created files from an agent's worktree back into the shared workspace."""
    proj_dir = ensure_project_initialized(project_name)
    safe_agent = re.sub(r"[^A-Za-z0-9_\-]", "", agent_id)
    wt_dir = (proj_dir / ".worktrees" / safe_agent).resolve()
    if not wt_dir.exists():
        raise ValueError(f"Worktree for agent {agent_id!r} does not exist")

    wt_diff = collect_directory_diff(wt_dir)
    merged_files: list[str] = []

    for item in wt_diff["changed_files"]:
        rel_path = item["path"]
        status_code = item["status"]
        src = wt_dir / rel_path
        dst = proj_dir / rel_path
        if status_code == "D":
            if dst.exists():
                dst.unlink()
                merged_files.append(rel_path)
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            merged_files.append(rel_path)

    if auto_commit and merged_files:
        _run_git(proj_dir, ["add", "-A"])
        _run_git(proj_dir, ["commit", "-m", f"feat({safe_agent}): merge agent worktree changes"])

    state = get_workspace_status(proj_dir.name)
    state["merged_agent"] = safe_agent
    state["merged_files"] = merged_files
    state["copied_files"] = merged_files
    return state


def commit_shared_workspace(message: str = "", project_name: str | None = None) -> dict[str, Any]:
    """Commit all current changes in the shared project directory as a baseline snapshot."""
    proj_dir = ensure_project_initialized(project_name)
    commit_msg = (message or "").strip() or f"snapshot: shared workspace update ({time.strftime('%Y-%m-%d %H:%M:%S')})"
    _run_git(proj_dir, ["add", "-A"])
    proc = _run_git(proj_dir, ["commit", "-m", commit_msg])
    state = get_workspace_status(proj_dir.name)
    state["commit_output"] = (proc.stdout or proc.stderr or "").strip()
    return state
