"""test_state.py -- JSON spec(에이전트 협력·진화도)과 산출물 버전 누적 단위 테스트.

LLM 없이 결정론적으로 검증한다.
"""

import json

from documentation_agent.contracts import InterfaceContract
from documentation_agent.evolution import ContractChange, EvolutionEntry, EvolutionLog
from documentation_agent.rag_proposal import (
    RagProposalResult,
    load_state,
    next_run_id,
    save_run,
    write_artifacts,
)


def _contract(name: str, role: str = "Retriever") -> InterfaceContract:
    return InterfaceContract(
        name=name, role=role,
        inputs=["query"], outputs=["docs"],
        preconditions=["ready"], postconditions=["done"],
    )


def _result(request="RAG", contracts=None, entries=None) -> RagProposalResult:
    return RagProposalResult(
        user_request=request,
        requirements_doc="# 요구사항",
        final_contracts=contracts if contracts is not None else [_contract("retriever")],
        evolution_log=EvolutionLog(entries=entries or []),
        yaml="steps: []",
        contracts_mermaid="flowchart LR\n",
    )


def test_next_run_id_starts_at_one(tmp_path):
    assert next_run_id(tmp_path) == 1


def test_save_run_accumulates_runs(tmp_path):
    save_run(_result("RAG1", contracts=[_contract("a")]), tmp_path, run_id=1)
    save_run(_result("RAG2", contracts=[_contract("a"), _contract("b", "Ranker")]), tmp_path, run_id=2)

    data = json.loads((tmp_path / "rag_state.json").read_text(encoding="utf-8"))
    assert data["spec_version"] == "1.0"
    assert len(data["runs"]) == 2
    assert [r["run_id"] for r in data["runs"]] == [1, 2]
    assert data["latest_run_id"] == 2
    # 산출물 경로가 run_001/run_002 로 버전 기록됨
    assert data["runs"][0]["artifacts"]["yaml"] == "versions/run_001/rag_proposal.generated.yaml"
    assert data["runs"][1]["artifacts"]["yaml"] == "versions/run_002/rag_proposal.generated.yaml"
    assert next_run_id(tmp_path) == 3


def test_load_state_returns_latest_run(tmp_path):
    entries1 = [EvolutionEntry(
        iteration=1, agent="RetrieverAgent", role="Retriever",
        proposals=["b"], critiques=["c1"],
        changes=[ContractChange(action="add", name="b", detail="신규")],
        add_count=1, evolution_degree=1,
    )]
    save_run(_result("RAG1", contracts=[_contract("a")], entries=entries1), tmp_path, run_id=1)

    entries2 = [EvolutionEntry(
        iteration=2, agent="RankerAgent", role="Ranker",
        proposals=["c"], critiques=[],
        changes=[ContractChange(action="add", name="c", detail="신규")],
        add_count=1, evolution_degree=1,
    )]
    save_run(_result("RAG2", contracts=[_contract("a"), _contract("c", "Ranker")], entries=entries2), tmp_path, run_id=2)

    contracts, log = load_state(tmp_path)
    assert contracts is not None
    assert [c.name for c in contracts] == ["a", "c"]  # 최신 run 의 계약
    assert len(log.entries) == 1
    assert log.entries[0].agent == "RankerAgent"
    assert log.entries[0].role == "Ranker"
    assert log.entries[0].proposals == ["c"]
    assert log.entries[0].evolution_degree == 1


def test_load_state_returns_none_when_missing(tmp_path):
    contracts, log = load_state(tmp_path)
    assert contracts is None
    assert log is None


def test_write_artifacts_versions_files(tmp_path):
    result = _result("RAG", contracts=[_contract("a")])
    version_dir = write_artifacts(result, tmp_path, run_id=1)
    # 버전 디렉터리에 저장
    assert (version_dir / "rag_proposal.generated.yaml").is_file()
    assert (version_dir / "contracts_graph.md").is_file()
    assert (version_dir / "rag_proposal.summary.json").is_file()
    # 최신(docs/)에도 갱신
    assert (tmp_path / "rag_proposal.generated.yaml").is_file()
    # summary.json 에 진화도 포함
    summary = json.loads((version_dir / "rag_proposal.summary.json").read_text(encoding="utf-8"))
    assert summary["run_id"] == 1
    assert "evolution_degree_total" in summary

