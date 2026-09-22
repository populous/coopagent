"""evolution.py -- 계약 병합, 충돌 검출, 불변조건 검증, 진화 로그.

이슈 #1 목표 5(판정 노드: 병합·충돌 검출·불변조건 검증)와 목표 6(진화 로그)을
구현한다. LLM 없이 결정론적으로 동작하므로 단위 테스트가 가능하다.
"""

from typing import List

from pydantic import BaseModel, Field

from .contracts import InterfaceContract


def merge_contracts(
    base: List[InterfaceContract],
    proposals: List[InterfaceContract],
) -> List[InterfaceContract]:
    """base 계약 목록에 proposals를 병합한다.

    - 이름(name)이 같은 계약은 proposals 쪽으로 덮어쓴다(강화).
    - 새 이름은 뒤에 추가한다(추가).
    - base에만 있고 proposals에 없는 것은 유지한다.
    """
    merged: dict = {c.name: c for c in base}
    for proposal in proposals:
        merged[proposal.name] = proposal
    return list(merged.values())


def detect_conflicts(contracts: List[InterfaceContract]) -> List[str]:
    """계약 집합 내 구조적 충돌/중복을 찾아 문구 목록으로 돌려준다."""
    conflicts: List[str] = []
    seen_names: dict = {}
    for c in contracts:
        if not c.name:
            conflicts.append("이름이 없는 계약이 존재합니다.")
            continue
        if not c.role:
            conflicts.append(f"역할(role)이 비어 있는 계약: {c.name}")
        if c.name in seen_names:
            conflicts.append(
                f"중복된 계약 이름: {c.name} (기존 role={seen_names[c.name]})"
            )
        else:
            seen_names[c.name] = c.role
    return conflicts


def validate_invariants(contracts: List[InterfaceContract]) -> List[str]:
    """각 계약이 구조적 불변조건을 만족하는지 검증한다.

    - inputs/outputs가 최소 1개 이상인가
    - preconditions/postconditions가 비어 있지 않은가
    """
    issues: List[str] = []
    for c in contracts:
        if not c.inputs:
            issues.append(f"{c.name}: inputs가 비어 있습니다.")
        if not c.outputs:
            issues.append(f"{c.name}: outputs가 비어 있습니다.")
        if not c.preconditions:
            issues.append(f"{c.name}: preconditions가 비어 있습니다.")
        if not c.postconditions:
            issues.append(f"{c.name}: postconditions가 비어 있습니다.")
    return issues


class ContractChange(BaseModel):
    """계약 한 건의 진화 이력(추가/삭제/강화)."""

    action: str = Field(..., description="add | remove | reinforce")
    name: str = Field(..., description="대상 계약 이름")
    detail: str = Field(default="", description="변경 내용 설명")


class EvolutionEntry(BaseModel):
    """한 반복(iteration)에서 일어난 변경 묶음."""

    iteration: int
    agent: str = Field(default="", description="변경을 일으킨 에이전트")
    changes: List[ContractChange] = Field(default_factory=list)


class EvolutionLog(BaseModel):
    """계약 진화 이력(추가/삭제/강화)을 기록하는 로그."""

    entries: List[EvolutionEntry] = Field(default_factory=list)

    def record(self, iteration: int, agent: str, changes: List[ContractChange]) -> None:
        self.entries.append(EvolutionEntry(iteration=iteration, agent=agent, changes=changes))

    def to_dicts(self) -> List[dict]:
        return [entry.model_dump() for entry in self.entries]


def diff_contracts(
    before: List[InterfaceContract],
    after: List[InterfaceContract],
) -> List[ContractChange]:
    """두 계약 집합을 비교해 추가/삭제/강화 이력을 만든다."""
    before_by_name = {c.name: c for c in before}
    after_by_name = {c.name: c for c in after}
    changes: List[ContractChange] = []

    for name, contract in after_by_name.items():
        if name not in before_by_name:
            changes.append(ContractChange(action="add", name=name, detail="새 계약 추가"))
        elif before_by_name[name] != contract:
            changes.append(ContractChange(action="reinforce", name=name, detail="계약 강화/수정"))

    for name in before_by_name:
        if name not in after_by_name:
            changes.append(ContractChange(action="remove", name=name, detail="계약 제거"))

    return changes
