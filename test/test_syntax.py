"""syntax.py YAML 직렬화 백엔드 단위 테스트."""

import yaml

from documentation_agent.contracts import InterfaceContract
from documentation_agent.syntax import YamlWorkflowBackend, render_workflow_spec


def _contracts():
    return [
        InterfaceContract(
            name="retrieve", role="Retriever", inputs=["query"], outputs=["docs"]
        ),
        InterfaceContract(
            name="rank", role="Ranker", inputs=["docs"], outputs=["ranked_docs"]
        ),
    ]


def test_yaml_backend_renders_steps_list():
    out = render_workflow_spec(_contracts(), YamlWorkflowBackend())
    data = yaml.safe_load(out)
    assert isinstance(data, dict)
    assert "steps" in data
    assert len(data["steps"]) == 2
    assert data["steps"][0]["name"] == "retrieve"
    assert data["steps"][0]["role"] == "Retriever"
    assert data["steps"][1]["outputs"] == ["ranked_docs"]


def test_render_workflow_spec_delegates_to_backend():
    class FakeBackend:
        def render(self, contracts):
            return "steps:" + ",".join(c.name for c in contracts)

    assert render_workflow_spec(_contracts(), FakeBackend()) == "steps:retrieve,rank"
