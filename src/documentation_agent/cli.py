import argparse
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from .mcp_registry import (
    MCP_TARGETS,
    check_mcp_status,
    default_settings_path,
    format_mcp_snippet,
    install_mcp_entry,
)
from .workflow import DocumentationAgent


def main() -> None:
    """CLI entrypoint for the documentation agent."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="사용자 요구에 기반해 요구사항 정의를 생성합니다",
    )
    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="만들고 싶은 애플리케이션이나 시스템에 대해 작성해 주세요 (생략 시 대화형 입력)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="생성할 페르소나 수를 설정해 주세요 (기본값: 5)",
    )
    parser.add_argument(
        "--graph",
        action="store_true",
        help="요구사항을 그래프로 구조화해 Mermaid 로 함께 출력·저장",
    )

    mcp_group = parser.add_argument_group("MCP (Cline/OpenCode 연동) 설정")
    mcp_group.add_argument("--mcp-print", action="store_true",
                           help="MCP 설정에 넣을 JSON 조각을 출력하고 종료")
    mcp_group.add_argument("--mcp-status", action="store_true",
                           help="이 프로젝트가 등록되어 있는지 확인하고 종료")
    mcp_group.add_argument("--mcp-install", action="store_true",
                           help="설정 파일에 이 프로젝트를 자동으로 등록하고 종료")
    mcp_group.add_argument("--force", action="store_true",
                           help="--mcp-install 시 기존 등록을 덮어쓴다")
    mcp_group.add_argument("--mcp-target", choices=list(MCP_TARGETS), default="cline",
                           help="대상 클라이언트: cline(기본) 또는 opencode")
    mcp_group.add_argument("--mcp-settings", default=None,
                           help="MCP 설정 파일 경로 (생략하면 대상의 기본 경로)")

    args = parser.parse_args()

    if args.mcp_print:
        print(format_mcp_snippet(args.mcp_target))
        return
    if args.mcp_status or args.mcp_install:
        settings_path = (Path(args.mcp_settings) if args.mcp_settings
                         else default_settings_path(args.mcp_target))
    if args.mcp_status:
        code, message = check_mcp_status(settings_path, args.mcp_target)
        print(message)
        raise SystemExit(code)
    if args.mcp_install:
        code, message = install_mcp_entry(settings_path, args.mcp_target,
                                          force=args.force)
        print(message)
        raise SystemExit(code)

    task = args.task
    if not task:
        task = input("만들고 싶은 애플리케이션이나 시스템을 설명해 주세요: ").strip()
    if not task:
        parser.error("--task 값 또는 대화형 입력이 필요합니다.")

    llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
    agent = DocumentationAgent(llm=llm, k=args.k, build_graph=args.graph)

    if args.graph:
        final_state = agent.run_full(task)
        print(final_state["requirements_doc"])
        mermaid = final_state["requirement_graph_mermaid"]
        print("\n=== 요구사항 그래프 (Mermaid) ===\n")
        print(mermaid)
        out_dir = Path("docs")
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "requirements_graph.md").write_text(
            f"# 요구사항 그래프\n\n```mermaid\n{mermaid}\n```\n", encoding="utf-8"
        )
        print(f"\n저장: {out_dir / 'requirements_graph.md'}")
    else:
        final_output = agent.run(user_request=task)
        print(final_output)


if __name__ == "__main__":
    main()
