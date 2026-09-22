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
