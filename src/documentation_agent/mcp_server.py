"""mcp_server.py -- coopagent 를 OpenCode/Cline 의 TUI 에 MCP 로 노출하는 서버.

MCP 의 stdio 전송(줄 단위 JSON-RPC 2.0)을 표준 라이브러리로 직접 구현한다.
검색/생성 로직은 documentation_agent.workflow.DocumentationAgent 와
documentation_agent.rag_proposal.run_proposal 을 그대로 재사용한다.

제공 도구(tools):
  * generate_requirements(task, k)      : 페르소나 인터뷰 -> 요구사항 문서 (LLM)
  * propose_rag_contracts(task, k, out) : 계약 합성 + 멀티 에이전트 제안/비판 -> YAML (쓰기)
  * list_generated_proposals()          : 생성된 산출물 목록 (읽기)
  * get_proposal_contracts(path)        : 산출물 파일 내용 (읽기)

주의: stdout 은 MCP 프로토콜 전용이다. 로그는 반드시 stderr 로 보낸다.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any

# 경로 설정: src/ 를 임포트 경로에, 프로젝트 루트(src 의 부모)를 데이터 기준으로.
_SRC_ROOT = Path(__file__).resolve().parent.parent   # src/
PROJECT_DIR = _SRC_ROOT.parent                        # 프로젝트 루트
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_DIR / ".env")

from langchain_openai import ChatOpenAI  # noqa: E402

from documentation_agent.rag_proposal import (  # noqa: E402
    load_state,
    next_run_id,
    run_proposal,
    save_run,
    write_artifacts,
)
from documentation_agent.workflow import DocumentationAgent  # noqa: E402

SERVER_NAME = "coopagent"
SERVER_VERSION = "0.2.0"
DEFAULT_PROTOCOL = "2025-06-18"
SUPPORTED_PROTOCOLS = {"2024-11-05", "2025-03-26", "2025-06-18"}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "generate_requirements",
        "description": (
            "사용자 요청으로부터 페르소나 인터뷰를 수행해 요구사항 문서를 생성한다. "
            "LLM을 여러 차례 호출하므로 수십 초~수 분 걸릴 수 있다."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "만들고 싶은 시스템/애플리케이션에 대한 설명",
                },
                "k": {
                    "type": "integer",
                    "description": "생성할 페르소나 수 (기본 5)",
                    "default": 5,
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "propose_rag_contracts",
        "description": (
            "사용자 요청으로부터 인터페이스 계약을 합성하고, 역할 멀티 에이전트가 "
            "제안·비판해 최종 계약 YAML 을 생성한다. docs/ 에 파일을 저장하는 쓰기 "
            "도구. LLM 호출이 많아 수 분 걸릴 수 있다. 자동 승인 목록에 넣지 말 것."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "RAG 등 시스템 구축 요청 (실사례 근거 포함)",
                },
                "k": {
                    "type": "integer",
                    "description": "생성할 페르소나 수 (기본 5)",
                    "default": 5,
                },
                "out": {
                    "type": "string",
                    "description": "결과 저장 디렉터리 (기본 docs)",
                    "default": "docs",
                },
                "fresh": {
                    "type": "boolean",
                    "description": "이전 기록(상태)을 무시하고 새로 시작 (기본 false)",
                    "default": False,
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "list_generated_proposals",
        "description": (
            "coopagent 가 생성한 제안 산출물(docs/ 의 요구사항 문서·YAML 계약·요약) "
            "목록을 돌려준다."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_proposal_contracts",
        "description": (
            "생성된 산출물 파일의 내용을 돌려준다(기본: docs/rag_proposal.generated.yaml)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "읽을 파일 경로 (기본 docs/rag_proposal.generated.yaml)",
                },
            },
        },
    },
]

def _make_llm() -> ChatOpenAI:
    """구조화 출력/생성에 쓰는 LLM. cli.py 와 동일 설정."""
    return ChatOpenAI(model="gpt-4o", temperature=0.0)


def log(message: str) -> None:
    """진단 로그는 stderr 로만 출력한다(stdout 은 MCP 전용)."""
    print(f"[{SERVER_NAME}] {message}", file=sys.stderr, flush=True)


def make_result(request_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def make_error(request_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id,
            "error": {"code": code, "message": message}}


def text_content(text: str) -> dict:
    """도구 실행 결과를 MCP content 배열 형태로 감싼다."""
    return {"content": [{"type": "text", "text": text}]}


# --------------------------------------------------------------------------
# 도구 구현
# --------------------------------------------------------------------------

def tool_generate_requirements(args: dict) -> dict:
    task = str(args.get("task", "")).strip()
    if not task:
        return text_content("오류: task 인자가 필요합니다.")
    k = max(1, int(args.get("k", 5) or 5))

    try:
        llm = _make_llm()
        agent = DocumentationAgent(llm=llm, k=k, build_graph=True)
        state = agent.run_full(task)
        doc = state["requirements_doc"]
        mermaid = state["requirement_graph_mermaid"]
    except Exception as exc:  # noqa: BLE001
        log(traceback.format_exc())
        return text_content(f"요구사항 문서 생성 실패: {exc}")

    return text_content(doc + "\n\n=== 요구사항 그래프 (Mermaid) ===\n\n" + mermaid)


def tool_propose_rag_contracts(args: dict) -> dict:
    task = str(args.get("task", "")).strip()
    if not task:
        return text_content("오류: task 인자가 필요합니다.")
    k = max(1, int(args.get("k", 5) or 5))
    out = str(args.get("out") or "docs")
    fresh = bool(args.get("fresh", False))

    try:
        llm = _make_llm()
        out_dir = PROJECT_DIR / out
        run_id = next_run_id(out_dir)
        existing_contracts, prior_log = (None, None) if fresh else load_state(out_dir)
        result = run_proposal(task, llm, k=k,
                              existing_contracts=existing_contracts, prior_log=prior_log)
        write_artifacts(result, out_dir, run_id)
        save_run(result, out_dir, run_id)
    except Exception as exc:  # noqa: BLE001
        log(traceback.format_exc())
        return text_content(f"계약 제안 생성 실패: {exc}")

    summary = (
        f"계약 수: baseline={len(result.baseline_contracts)}, "
        f"final={len(result.final_contracts)}\n"
        f"충돌: {len(result.conflicts)}건, 불변조건 위반: {len(result.invariant_issues)}건\n"
        f"산출물 저장: {out}/\n\n"
        f"{result.yaml}"
    )
    return text_content(summary)


def tool_list_generated_proposals(_args: dict) -> dict:
    docs_dir = PROJECT_DIR / "docs"
    if not docs_dir.is_dir():
        return text_content("docs/ 디렉터리가 없습니다. 아직 제안을 생성하지 않았습니다.")
    files = sorted(p for p in docs_dir.iterdir() if p.is_file())
    if not files:
        return text_content("생성된 산출물이 없습니다.")
    lines = [f"산출물 {len(files)}개 (docs/)", ""]
    for path in files:
        lines.append(f"{path.stat().st_size:7d}  {path.name}")
    return text_content("\n".join(lines))


def tool_get_proposal_contracts(args: dict) -> dict:
    raw = str(args.get("path") or "docs/rag_proposal.generated.yaml")
    path = (PROJECT_DIR / raw).resolve()
    # 프로젝트 루트 밖 경로 접근 방지
    if path != PROJECT_DIR and PROJECT_DIR not in path.parents:
        return text_content(f"허용되지 않은 경로입니다: {raw}")
    if not path.is_file():
        return text_content(f"파일이 없습니다: {raw}")
    try:
        return text_content(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return text_content(f"파일을 읽을 수 없습니다: {raw}\n({exc})")


TOOL_HANDLERS = {
    "generate_requirements": tool_generate_requirements,
    "propose_rag_contracts": tool_propose_rag_contracts,
    "list_generated_proposals": tool_list_generated_proposals,
    "get_proposal_contracts": tool_get_proposal_contracts,
}

# --------------------------------------------------------------------------
# MCP 프로토콜 처리
# --------------------------------------------------------------------------

def handle_request(message: dict) -> dict | None:
    """JSON-RPC 요청 하나를 처리한다. 알림(notification)이면 None 을 돌려준다."""
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    if request_id is None:
        return None

    if method == "initialize":
        requested = params.get("protocolVersion")
        protocol = requested if requested in SUPPORTED_PROTOCOLS else DEFAULT_PROTOCOL
        return make_result(request_id, {
            "protocolVersion": protocol,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })

    if method == "ping":
        return make_result(request_id, {})

    if method == "tools/list":
        return make_result(request_id, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        handler = TOOL_HANDLERS.get(str(name))
        if handler is None:
            return make_error(request_id, -32602, f"알 수 없는 도구: {name}")
        try:
            return make_result(request_id, handler(arguments))
        except Exception as exc:  # noqa: BLE001
            log(traceback.format_exc())
            return make_result(request_id, text_content(f"도구 실행 오류: {exc}"))

    return make_error(request_id, -32601, f"지원하지 않는 메서드: {method}")


def serve(stdin=None, stdout=None) -> int:
    """stdio 전송으로 MCP 메시지 루프를 돈다(줄 단위 JSON-RPC)."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout

    for stream in (stdin, stdout):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(newline="\n", encoding="utf-8")
            except (ValueError, OSError):
                pass

    err_reconfigure = getattr(sys.stderr, "reconfigure", None)
    if callable(err_reconfigure):
        try:
            err_reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

    log(f"시작됨 (도구 {len(TOOLS)}개, 프로젝트 {PROJECT_DIR})")

    for raw_line in stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response = make_error(None, -32700, "JSON 파싱 오류")
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()
            continue

        try:
            response = handle_request(message)
        except Exception as exc:  # noqa: BLE001
            log(traceback.format_exc())
            response = make_error(message.get("id"), -32603, f"내부 오류: {exc}")

        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()

    log("stdin 종료, 서버를 닫습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(serve())
