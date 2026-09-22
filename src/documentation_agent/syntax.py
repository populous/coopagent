import re
from typing import List, Protocol

from .contracts import InterfaceContract
from .models import RequirementGraph


class SyntaxBackend(Protocol):
    """컨트랙트 리스트를 특정 DSL/포맷으로 직렬화하는 백엔드 인터페이스"""

    def render(self, contracts: List[InterfaceContract]) -> str:
        ...


class YamlWorkflowBackend:
    """간단한 YAML 기반 워크플로 스펙 렌더러"""

    def render(self, contracts: List[InterfaceContract]) -> str:
        import yaml

        steps = []
        for c in contracts:
            steps.append(
                {
                    "name": c.name,
                    "role": c.role,
                    "inputs": c.inputs,
                    "outputs": c.outputs,
                    "preconditions": c.preconditions,
                    "postconditions": c.postconditions,
                    "failure_modes": c.failure_modes,
                    "metrics": c.metrics,
                }
            )

        return yaml.dump({"steps": steps}, allow_unicode=True, sort_keys=False)


def render_workflow_spec(contracts: List[InterfaceContract], backend: SyntaxBackend) -> str:
    """컨트랙트 집합을 주어진 백엔드로 직렬화"""

    return backend.render(contracts)


_CATEGORY_CLASSES = {
    "functional": "functional",
    "non_functional": "non_functional",
    "constraint": "constraint",
    "risk": "risk",
}


def render_requirement_mermaid(graph: RequirementGraph) -> str:
    """RequirementGraph 를 Mermaid flowchart 로 렌더링한다.

    노드는 요구사항(id: 제목), 엣지는 depends_on(선행 -> 후행) 관계다.
    카테고리별로 색상 클래스를 적용한다.
    """
    lines = [
        "flowchart TD",
        "    classDef functional fill:#d5e8d4,stroke:#82b366",
        "    classDef non_functional fill:#dae8fc,stroke:#6c8ebf",
        "    classDef constraint fill:#fff2cc,stroke:#d6b656",
        "    classDef risk fill:#f8cecc,stroke:#b85450",
    ]

    for node in graph.nodes:
        label = f"{node.id}: {node.title}"
        safe_label = label.replace('"', "'")
        cls = _CATEGORY_CLASSES.get(node.category, "functional")
        lines.append(f'    {node.id}["{safe_label}"]:::{cls}')

    for node in graph.nodes:
        for dep in node.depends_on:
            lines.append(f"    {dep} --> {node.id}")

    return "\n".join(lines)


_ROLE_CLASSES = {
    "Retriever": "retriever",
    "Ranker": "ranker",
    "Orchestrator": "orchestrator",
    "Evaluator": "evaluator",
    "Logger": "logger",
    "Optimizer": "optimizer",
    "Visualizer": "visualizer",
}

_ROLE_COLORS = {
    "retriever": "fill:#d5e8d4,stroke:#82b366",
    "ranker": "fill:#dae8fc,stroke:#6c8ebf",
    "orchestrator": "fill:#fff2cc,stroke:#d6b656",
    "evaluator": "fill:#e1d5e7,stroke:#9673a6",
    "logger": "fill:#f8cecc,stroke:#b85450",
    "optimizer": "fill:#f5f5f5,stroke:#666666",
    "visualizer": "fill:#ffe6cc,stroke:#d79b00",
}


def _slug(name: str) -> str:
    """계약 이름을 Mermaid 노드 id 로 쓸 수 있는 안전한 식별자로 바꾼다."""
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or "node"


def _tokens(text: str) -> set:
    """데이터 흐름 비교용 의미 토큰(2자 초과 영숫자 단어) 집합."""
    return {w.lower() for w in re.findall(r"[A-Za-z0-9]+", text) if len(w) > 2}


def render_contract_mermaid(contracts: List[InterfaceContract]) -> str:
    """InterfaceContract 목록을 Mermaid 그래프로 렌더링한다.

    노드는 계약(name+role, 역할별 색상), 엣지는 데이터 흐름(outputs 와 inputs 의
    의미 토큰 겹침)이다.
    """
    lines = ["flowchart LR"]
    for cls, color in _ROLE_COLORS.items():
        lines.append(f"    classDef {cls} {color}")

    for c in contracts:
        node_id = _slug(c.name)
        cls = _ROLE_CLASSES.get(c.role, "orchestrator")
        label = f"{c.name}<br/>({c.role})"
        safe_label = label.replace('"', "'")
        lines.append(f'    {node_id}["{safe_label}"]:::{cls}')

    # 데이터 흐름 엣지: A 의 outputs 와 B 의 inputs 가 의미적으로 겹치면 A -> B
    for a in contracts:
        a_out: set = set()
        for o in a.outputs:
            a_out |= _tokens(o)
        if not a_out:
            continue
        for b in contracts:
            if a.name == b.name:
                continue
            b_in: set = set()
            for i in b.inputs:
                b_in |= _tokens(i)
            if a_out & b_in:
                lines.append(f"    {_slug(a.name)} --> {_slug(b.name)}")

    return "\n".join(lines)
