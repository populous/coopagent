from typing import List, Protocol

from .contracts import InterfaceContract


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
