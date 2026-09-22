"""rag_proposal.py -- coopagent 자체 파이프라인으로 RAG 계약 제안을 생성하는 드라이버.

이슈 #1의 '완료 조건'을 한 흐름으로 실행한다:
  1. RAG 요청 -> 페르소나 인터뷰 (DocumentationAgent)
  2. 인터뷰 결과 -> ContractSynthesizer (baseline 계약 합성)
  3. 역할 에이전트(Retriever/Ranker/Orchestrator/Evaluator/Logger) 제안/비판 루프
  4. 병합 + 충돌 검출 + 불변조건 검증 (판정 노드)
  5. 진화 로그 기록
  6. YAML 직렬화

사용 예:
    python -m documentation_agent.rag_proposal --task "RAG 시스템 구축 요청 ..." --out docs
"""

import argparse
import json
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .contract_synthesis import ContractSynthesizer
from .contracts import InterfaceContract
from .evolution import (
    EvolutionLog,
    detect_conflicts,
    diff_contracts,
    merge_contracts,
    validate_invariants,
)
from .models import Interview
from .syntax import YamlWorkflowBackend, render_workflow_spec
from .workflow import DocumentationAgent

from agents.base import AgentContext
from agents.evaluator import EvaluatorAgent
from agents.logger import LoggerAgent
from agents.orchestrator import OrchestratorAgent
from agents.rag_retriever import RetrieverAgent
from agents.ranker import RankerAgent


def build_agents(llm: ChatOpenAI) -> List:
    """역할 에이전트들을 생성 순서대로 돌려준다."""
    return [
        RetrieverAgent(llm),
        RankerAgent(llm),
        OrchestratorAgent(llm),
        EvaluatorAgent(llm),
        LoggerAgent(llm),
    ]


class RagProposalResult(BaseModel):
    """coopagent 파이프라인이 만들어낸 RAG 제안 결과 전체."""

    user_request: str
    requirements_doc: str
    interviews: List[Interview] = Field(default_factory=list)
    baseline_contracts: List[InterfaceContract] = Field(default_factory=list)
    final_contracts: List[InterfaceContract] = Field(default_factory=list)
    critiques: dict = Field(default_factory=dict)
    evolution_log: EvolutionLog = Field(default_factory=EvolutionLog)
    conflicts: List[str] = Field(default_factory=list)
    invariant_issues: List[str] = Field(default_factory=list)
    yaml: str = ""


def run_proposal(user_request: str, llm: ChatOpenAI, k: int = 5) -> RagProposalResult:
    """coopagent 파이프라인을 실제로 실행해 RAG 계약 제안을 만든다."""
    # 1) 페르소나 인터뷰 -> 요구사항 문서 + 인터뷰 결과
    doc_agent = DocumentationAgent(llm=llm, k=k)
    final_state = doc_agent.run_full(user_request)
    interviews: List[Interview] = final_state.get("interviews", [])
    requirements_doc: str = final_state.get("requirements_doc", "")

    # 2) 인터뷰 결과 -> baseline 계약 합성
    synthesizer = ContractSynthesizer(llm=llm)
    baseline = synthesizer.run(user_request, interviews)

    # 3) 역할 에이전트 제안/비판 루프 (각 에이전트가 1회씩 반복)
    working = list(baseline)
    evolution_log = EvolutionLog()
    critiques: dict = {}

    for iteration, agent in enumerate(build_agents(llm), start=1):
        context = AgentContext(
            user_request=user_request,
            interviews=interviews,
            existing_contracts=working,
        )
        proposals = agent.propose_contracts(context)
        agent_critiques = agent.critique_contracts(context, working)
        critiques[agent.role] = agent_critiques

        before = list(working)
        working = merge_contracts(working, proposals)
        changes = diff_contracts(before, working)
        evolution_log.record(iteration, agent.role, changes)

    # 4) 판정 노드: 충돌/불변조건 검증
    conflicts = detect_conflicts(working)
    invariant_issues = validate_invariants(working)

    # 5) YAML 직렬화
    yaml_str = render_workflow_spec(working, YamlWorkflowBackend())

    return RagProposalResult(
        user_request=user_request,
        requirements_doc=requirements_doc,
        interviews=interviews,
        baseline_contracts=baseline,
        final_contracts=working,
        critiques=critiques,
        evolution_log=evolution_log,
        conflicts=conflicts,
        invariant_issues=invariant_issues,
        yaml=yaml_str,
    )


def write_artifacts(result: RagProposalResult, out_dir: Path) -> None:
    """결과물(요구사항 문서, YAML, 진화 로그, 요약 JSON)을 디렉터리에 저장한다."""
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "rag_proposal.requirements.md").write_text(
        result.requirements_doc, encoding="utf-8"
    )
    (out_dir / "rag_proposal.generated.yaml").write_text(result.yaml, encoding="utf-8")

    summary = {
        "user_request": result.user_request,
        "critiques": result.critiques,
        "evolution_log": result.evolution_log.to_dicts(),
        "conflicts": result.conflicts,
        "invariant_issues": result.invariant_issues,
        "baseline_contract_count": len(result.baseline_contracts),
        "final_contract_count": len(result.final_contracts),
    }
    (out_dir / "rag_proposal.summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main(argv: List[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="coopagent 파이프라인으로 RAG 계약 제안을 생성합니다."
    )
    parser.add_argument("--task", type=str, default=None,
                        help="RAG 시스템 구축 요청 (실사례 근거 포함, 생략 시 대화형 입력)")
    parser.add_argument("--k", type=int, default=5, help="생성할 페르소나 수")
    parser.add_argument("--out", type=str, default="docs",
                        help="결과 저장 디렉터리 (기본 docs)")
    args = parser.parse_args(argv)
    task = args.task
    if not task:
        task = input("RAG 시스템 구축 요청을 설명해 주세요: ").strip()
    if not task:
        parser.error("--task 값 또는 대화형 입력이 필요합니다.")

    llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
    result = run_proposal(task, llm, k=args.k)

    write_artifacts(result, Path(args.out))

    print("=== 최종 계약 (YAML) ===")
    print(result.yaml)
    print()
    print(f"계약 수: baseline={len(result.baseline_contracts)}, "
          f"final={len(result.final_contracts)}")
    print(f"충돌: {len(result.conflicts)}건, 불변조건 위반: {len(result.invariant_issues)}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
