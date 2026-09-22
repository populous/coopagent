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
from datetime import datetime
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .contract_synthesis import ContractSynthesizer
from .contracts import InterfaceContract
from .evolution import (
    ContractChange,
    EvolutionEntry,
    EvolutionLog,
    detect_conflicts,
    diff_contracts,
    merge_contracts,
    validate_invariants,
)
from .models import Interview
from .syntax import YamlWorkflowBackend, render_contract_mermaid, render_workflow_spec
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
    contracts_mermaid: str = ""


def run_proposal(
    user_request: str,
    llm: ChatOpenAI,
    k: int = 5,
    existing_contracts: List[InterfaceContract] | None = None,
    prior_log: EvolutionLog | None = None,
) -> RagProposalResult:
    """coopagent 파이프라인을 실제로 실행해 RAG 계약 제안을 만든다.

    existing_contracts/prior_log 를 주면 이전 상태(기록)에서 이어서 진화한다.
    """
    # 1) 페르소나 인터뷰 -> 요구사항 문서 + 인터뷰 결과
    doc_agent = DocumentationAgent(llm=llm, k=k)
    final_state = doc_agent.run_full(user_request)
    interviews: List[Interview] = final_state.get("interviews", [])
    requirements_doc: str = final_state.get("requirements_doc", "")

    # 2) 인터뷰 결과 -> baseline 계약 합성
    synthesizer = ContractSynthesizer(llm=llm)
    baseline = synthesizer.run(user_request, interviews)

    # 3) 작업 세트: 이전 계약이 있으면 그것을, 없으면 baseline 을 사용
    working = list(existing_contracts) if existing_contracts is not None else list(baseline)
    evolution_log = prior_log if prior_log is not None else EvolutionLog()
    critiques: dict = {}
    start_iteration = len(evolution_log.entries)

    for offset, agent in enumerate(build_agents(llm)):
        iteration = start_iteration + offset + 1
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
        evolution_log.record(
            iteration, agent.name, changes,
            role=agent.role,
            proposals=[p.name for p in proposals],
            critiques=agent_critiques,
        )

    # 4) 판정 노드: 충돌/불변조건 검증
    conflicts = detect_conflicts(working)
    invariant_issues = validate_invariants(working)

    # 5) YAML 직렬화 + 계약 그래프
    yaml_str = render_workflow_spec(working, YamlWorkflowBackend())
    contracts_mermaid = render_contract_mermaid(working)

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
        contracts_mermaid=contracts_mermaid,
    )


def write_artifacts(result: RagProposalResult, out_dir: Path, run_id: int) -> Path:
    """산출물(md/yaml/json)을 버전 디렉터리에 저장하고 최신(docs/)도 갱신한다."""
    out_dir.mkdir(parents=True, exist_ok=True)
    version_dir = out_dir / VERSIONS_DIR / f"run_{run_id:03d}"
    version_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "run_id": run_id,
        "user_request": result.user_request,
        "critiques": result.critiques,
        "evolution_log": result.evolution_log.to_dicts(),
        "evolution_degree_total": result.evolution_log.total_degree(),
        "conflicts": result.conflicts,
        "invariant_issues": result.invariant_issues,
        "baseline_contract_count": len(result.baseline_contracts),
        "final_contract_count": len(result.final_contracts),
    }
    summary_json = json.dumps(summary, ensure_ascii=False, indent=2)
    graph_md = f"# 계약 그래프\n\n```mermaid\n{result.contracts_mermaid}\n```\n"

    # 버전 디렉터리에 저장 (누적)
    (version_dir / "rag_proposal.requirements.md").write_text(result.requirements_doc, encoding="utf-8")
    (version_dir / "rag_proposal.generated.yaml").write_text(result.yaml, encoding="utf-8")
    (version_dir / "contracts_graph.md").write_text(graph_md, encoding="utf-8")
    (version_dir / "rag_proposal.summary.json").write_text(summary_json, encoding="utf-8")

    # 최신(docs/)에도 갱신
    (out_dir / "rag_proposal.requirements.md").write_text(result.requirements_doc, encoding="utf-8")
    (out_dir / "rag_proposal.generated.yaml").write_text(result.yaml, encoding="utf-8")
    (out_dir / "contracts_graph.md").write_text(graph_md, encoding="utf-8")
    (out_dir / "rag_proposal.summary.json").write_text(summary_json, encoding="utf-8")

    return version_dir


STATE_FILE = "rag_state.json"
SPEC_VERSION = "1.0"
VERSIONS_DIR = "versions"


def _load_state_data(out_dir: Path) -> dict:
    """상태 파일 전체(spec)를 읽는다. 없으면 빈 spec."""
    path = out_dir / STATE_FILE
    if not path.is_file():
        return {"spec_version": SPEC_VERSION, "runs": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"spec_version": SPEC_VERSION, "runs": []}
    data.setdefault("spec_version", SPEC_VERSION)
    data.setdefault("runs", [])
    return data


def next_run_id(out_dir: Path) -> int:
    """누적 run 개수 + 1 을 다음 run id 로 돌려준다."""
    return len(_load_state_data(out_dir)["runs"]) + 1


def load_state(out_dir: Path) -> tuple[List[InterfaceContract] | None, EvolutionLog | None]:
    """최신 run 의 계약/진화 로그를 읽어 이어서 진화하기 위한 입력으로 쓴다."""
    runs = _load_state_data(out_dir)["runs"]
    if not runs:
        return None, None
    latest = runs[-1]
    contracts = [InterfaceContract(**c) for c in latest.get("contracts", [])]
    entries = [
        EvolutionEntry(
            iteration=e["iteration"],
            agent=e.get("agent", ""),
            role=e.get("role", ""),
            proposals=list(e.get("proposals", [])),
            critiques=list(e.get("critiques", [])),
            changes=[ContractChange(**c) for c in e.get("changes", [])],
            add_count=e.get("add_count", 0),
            remove_count=e.get("remove_count", 0),
            reinforce_count=e.get("reinforce_count", 0),
            evolution_degree=e.get("evolution_degree", 0),
        )
        for e in latest.get("evolution_log", [])
    ]
    return contracts, EvolutionLog(entries=entries)


def save_run(result: RagProposalResult, out_dir: Path, run_id: int) -> Path:
    """이번 run 을 상태 파일의 runs 히스토리에 누적 기록한다."""
    data = _load_state_data(out_dir)
    artifact_base = f"{VERSIONS_DIR}/run_{run_id:03d}"
    run_record = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "user_request": result.user_request,
        "contracts_count": len(result.final_contracts),
        "contracts": [c.model_dump() for c in result.final_contracts],
        "evolution_log": result.evolution_log.to_dicts(),
        "evolution_degree_total": result.evolution_log.total_degree(),
        "artifacts": {
            "yaml": f"{artifact_base}/rag_proposal.generated.yaml",
            "summary": f"{artifact_base}/rag_proposal.summary.json",
            "requirements": f"{artifact_base}/rag_proposal.requirements.md",
            "contracts_graph": f"{artifact_base}/contracts_graph.md",
        },
    }
    data["runs"].append(run_record)
    data["latest_run_id"] = run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / STATE_FILE
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


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
    parser.add_argument("--fresh", action="store_true",
                        help="이전 기록(상태)을 무시하고 새로 시작")
    args = parser.parse_args(argv)
    task = args.task
    if not task:
        task = input("RAG 시스템 구축 요청을 설명해 주세요: ").strip()
    if not task:
        parser.error("--task 값 또는 대화형 입력이 필요합니다.")

    out_dir = Path(args.out)
    run_id = next_run_id(out_dir)
    existing_contracts = None
    prior_log = None
    if not args.fresh:
        existing_contracts, prior_log = load_state(out_dir)

    llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
    result = run_proposal(task, llm, k=args.k,
                          existing_contracts=existing_contracts, prior_log=prior_log)

    write_artifacts(result, out_dir, run_id)
    save_run(result, out_dir, run_id)

    print("=== 최종 계약 (YAML) ===")
    print(result.yaml)
    print()
    print(f"계약 수: baseline={len(result.baseline_contracts)}, "
          f"final={len(result.final_contracts)}")
    print(f"충돌: {len(result.conflicts)}건, 불변조건 위반: {len(result.invariant_issues)}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
