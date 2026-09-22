"""test_evolution.py -- 병합/충돌 검출/불변조건 검증/진화 로그 단위 테스트.

LLM 없이 결정론적으로 동작하는 evolution.py 를 검증한다.
"""

from documentation_agent.contracts import InterfaceContract
from documentation_agent.evolution import (
    ContractChange,
    EvolutionLog,
    detect_conflicts,
    diff_contracts,
    merge_contracts,
    validate_invariants,
)


def _contract(name: str, role: str = "Retriever", **kwargs) -> InterfaceContract:
    defaults = dict(
        name=name,
        role=role,
        inputs=kwargs.get("inputs", ["query"]),
        outputs=kwargs.get("outputs", ["docs"]),
        preconditions=kwargs.get("preconditions", ["index ready"]),
        postconditions=kwargs.get("postconditions", ["top-k returned"]),
        failure_modes=kwargs.get("failure_modes", ["empty index"]),
        metrics=kwargs.get("metrics", ["latency_ms"]),
    )
    return InterfaceContract(**defaults)


def test_merge_adds_new_and_keeps_existing():
    base = [_contract("retriever")]
    proposal = [_contract("ranker", role="Ranker")]
    merged = merge_contracts(base, proposal)
    assert {c.name for c in merged} == {"retriever", "ranker"}


def test_merge_overwrites_same_name():
    base = [_contract("retriever", inputs=["query"])]
    proposal = [_contract("retriever", inputs=["query", "sources"])]
    merged = merge_contracts(base, proposal)
    assert len(merged) == 1
    assert merged[0].inputs == ["query", "sources"]


def test_detect_conflicts_duplicate_name():
    contracts = [
        _contract("retriever", role="Retriever"),
        _contract("retriever", role="Ranker"),
    ]
    conflicts = detect_conflicts(contracts)
    assert any("중복된 계약 이름" in c for c in conflicts)


def test_detect_conflicts_empty_role():
    contracts = [_contract("retriever", role="")]
    conflicts = detect_conflicts(contracts)
    assert any("역할(role)이 비어" in c for c in conflicts)


def test_validate_invariants_missing_fields():
    contracts = [InterfaceContract(name="empty", role="Retriever")]
    issues = validate_invariants(contracts)
    assert len(issues) == 4  # inputs/outputs/preconditions/postconditions 모두 비어 있음


def test_validate_invariants_passes_when_complete():
    contracts = [_contract("retriever")]
    assert validate_invariants(contracts) == []


def test_diff_contracts_add_reinforce_remove():
    before = [_contract("retriever"), _contract("to_remove")]
    after = [_contract("retriever", inputs=["query", "k"]), _contract("ranker", role="Ranker")]
    changes = diff_contracts(before, after)
    actions = {c.name: c.action for c in changes}
    assert actions["ranker"] == "add"
    assert actions["retriever"] == "reinforce"
    assert actions["to_remove"] == "remove"


def test_evolution_log_records_entries():
    log = EvolutionLog()
    log.record(1, "Retriever", [ContractChange(action="add", name="ranker", detail="신규")])
    log.record(2, "Ranker", [ContractChange(action="reinforce", name="retriever", detail="강화")])
    assert len(log.entries) == 2
    assert [e.iteration for e in log.entries] == [1, 2]
    dumped = log.to_dicts()
    assert dumped[0]["agent"] == "Retriever"
    assert dumped[0]["changes"][0]["action"] == "add"
