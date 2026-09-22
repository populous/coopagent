"""mcp_registry.py -- coopagent MCP 서버를 Cline/OpenCode 에 등록하는 유틸.

Cline 과 OpenCode 의 MCP 설정 스키마 차이를 흡수해, 등록용 JSON 조각 생성·
등록 여부 확인·자동 등록을 제공한다. cli.py 의 --mcp-* 옵션에서 사용한다.
"""

from __future__ import annotations

import json
from pathlib import Path

MCP_SERVER_NAME = "coopagent"
MCP_TARGETS = ("cline", "opencode")

DEFAULT_MCP_SETTINGS_PATH = (
    Path.home() / ".cline" / "data" / "settings" / "cline_mcp_settings.json"
)
DEFAULT_OPENCODE_SETTINGS_PATH = Path.home() / ".config" / "opencode" / "opencode.json"

_SRC_ROOT = Path(__file__).resolve().parent.parent   # src/
PROJECT_DIR = _SRC_ROOT.parent                        # 프로젝트 루트


def _project_dir() -> Path:
    return PROJECT_DIR


def _venv_python_path() -> Path:
    return _project_dir() / ".venv" / "Scripts" / "python.exe"


def _server_path() -> Path:
    return _project_dir() / "src" / "documentation_agent" / "mcp_server.py"


def default_settings_path(target: str) -> Path:
    """target 에 맞는 기본 MCP 설정 파일 경로를 돌려준다."""
    if target == "opencode":
        return DEFAULT_OPENCODE_SETTINGS_PATH
    return DEFAULT_MCP_SETTINGS_PATH


def _servers_key(target: str) -> str:
    """설정 파일에서 서버 목록이 들어가는 최상위 키 이름."""
    return "mcp" if target == "opencode" else "mcpServers"


def build_mcp_entry(target: str = "cline") -> dict:
    """지정된 클라이언트 설정에 넣을 coopagent MCP 서버 조각을 만든다."""
    if target == "opencode":
        return {
            "type": "local",
            "command": [str(_venv_python_path()), str(_server_path())],
            "enabled": True,
        }
    return {
        "command": str(_venv_python_path()),
        "args": [str(_server_path())],
        "env": {},
        "disabled": False,
        "autoApprove": ["list_generated_proposals", "get_proposal_contracts"],
    }


def format_mcp_snippet(target: str = "cline") -> str:
    """등록용 JSON 조각을 문자열로 돌려준다."""
    payload = {_servers_key(target): {MCP_SERVER_NAME: build_mcp_entry(target)}}
    return json.dumps(payload, ensure_ascii=False, indent=2)


def check_mcp_status(settings_path: Path, target: str = "cline") -> tuple[int, str]:
    """등록 여부/경로 일치 여부를 확인하고 (exit_code, 메시지) 를 돌려준다."""
    venv_python = str(_venv_python_path())
    server = str(_server_path())
    key = _servers_key(target)
    if not settings_path.exists():
        return 1, (
            f"MCP 설정 파일이 없습니다: {settings_path}\n"
            "아직 해당 클라이언트를 실행하지 않았거나 경로가 다를 수 있습니다.\n"
            "--mcp-install 로 새로 만들 수 있습니다."
        )
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return 1, f"설정 파일을 읽을 수 없습니다: {settings_path}\n({exc})"

    servers = data.get(key, {})
    entry = servers.get(MCP_SERVER_NAME)
    if entry is None:
        return 1, (
            f"'{MCP_SERVER_NAME}' 서버가 아직 등록되어 있지 않습니다: {settings_path}\n"
            "--mcp-install 로 등록할 수 있습니다."
        )

    problems = []
    if target == "opencode":
        lines = [
            f"'{MCP_SERVER_NAME}' 등록됨: {settings_path}",
            f"  type    : {entry.get('type')}",
            f"  command : {entry.get('command')}",
            f"  enabled : {entry.get('enabled', True)}",
        ]
        if entry.get("command") != [venv_python, server]:
            problems.append("  경고: command 가 이 프로젝트의 .venv/서버 경로와 다릅니다.")
        if entry.get("enabled") is False:
            problems.append("  경고: enabled=false 라서 OpenCode 가 이 서버를 쓰지 않습니다")
    else:
        lines = [
            f"'{MCP_SERVER_NAME}' 등록됨: {settings_path}",
            f"  command : {entry.get('command')}",
            f"  args    : {entry.get('args')}",
            f"  disabled: {entry.get('disabled', False)}",
        ]
        if entry.get("command") != venv_python:
            problems.append("  경고: command 가 이 프로젝트의 .venv 경로와 다릅니다.")
        if entry.get("disabled"):
            problems.append("  경고: disabled=true 라서 Cline 이 이 서버를 쓰지 않습니다")

    if not Path(venv_python).exists():
        problems.append(f"  경고: {venv_python} 가 실제로 존재하지 않습니다 (setup.ps1 을 먼저 실행하세요)")

    if problems:
        lines.append("")
        lines.extend(problems)
        return 1, "\n".join(lines)
    return 0, "\n".join(lines)


def install_mcp_entry(settings_path: Path, target: str = "cline",
                      force: bool = False) -> tuple[int, str]:
    """설정 파일에 coopagent MCP 서버 항목을 병합해서 써준다."""
    key = _servers_key(target)
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return 1, f"기존 설정 파일을 읽을 수 없습니다: {settings_path}\n({exc})"
    else:
        data = {}

    servers = data.setdefault(key, {})
    if MCP_SERVER_NAME in servers and not force:
        return 1, (
            f"'{MCP_SERVER_NAME}' 은 이미 등록되어 있습니다: {settings_path}\n"
            "덮어쓰려면 --force 를 함께 쓰세요."
        )

    servers[MCP_SERVER_NAME] = build_mcp_entry(target)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0, f"'{MCP_SERVER_NAME}' 을 등록했습니다: {settings_path}"
