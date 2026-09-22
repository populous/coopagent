"""test_state.py -- 상태(기록) 저장/복원 단위 테스트.

save_state/load_state 가 최종 계약과 진화 로그를 파일로 기록하고 다시 읽어오는지
LLM 없이 결정론적으로 검증한다.
"""

from documentation_agent.contracts import InterfaceContract
from documentation_agent.evolution import ContractChange, EvolutionEntry, EvolutionLog
from documentation_agent.rag_proposal import RagProposalResult, load_state, save_state


def _contract(name: str, role: str = "Retriever") -> InterfaceContract:
    return InterfaceContract(
        name=name, role=role,
        inputs=["query"], outputs=["docs"],
        preconditions=["ready"], postconditions=["done"],
    )


def test_save_and_load_state_roundtrip(tmp_path):
    result = RagProposalResult(
        user_request="RAG",
        requirements_doc="# 요구사항",
        final_contracts=[_contract("retriever"), _contract("ranker", "Ranker")],
        evolution_log=EvolutionLog(entries=[
            EvolutionEntry(iteration=1, agent="Retriever", changes=[
                ContractChange(action="add", name="ranker", detail="신규"),
            ]),
        ]),
    )
    save_state(result, tmp_path)

    contracts, log = load_state(tmp_path)
    assert contracts is not None
    assert log is not None
    assert [c.name for c in contracts] == ["retriever", "ranker"]
    assert [c.role for c in contracts] == ["Retriever", "Ranker"]
    assert len(log.entries) == 1
    assert log.entries[0].agent == "Retriever"
    assert log.entries[0].changes[0].action == "add"


def test_load_state_returns_none_when_missing(tmp_path):
    contracts, log = load_state(tmp_path)
    assert contracts is None
    assert log is None


def test_load_state_ignores_corrupt_file(tmp_path):
    (tmp_path / "rag_state.json").write_text("{not valid json", encoding="utf-8")
    contracts, log = load_state(tmp_path)
    assert contracts is None
    assert log is None
