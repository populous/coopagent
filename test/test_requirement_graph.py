"""test_requirement_graph.py -- 요구사항 그래프 검증/렌더링 단위 테스트.

LLM 없이 결정론적으로 검증 가능한 부분(위상 정렬, 순환/중복/미존재 의존성 검출,
Mermaid 렌더링)을 검증한다.
"""

from documentation_agent.models import RequirementGraph, RequirementNode
from documentation_agent.requirement_graph import topological_sort, validate_graph
from documentation_agent.syntax import render_requirement_mermaid


def _node(id: str, deps=None, category: str = "functional") -> RequirementNode:
    return RequirementNode(
        id=id, title=f"요구사항 {id}", description="설명",
        category=category, depends_on=deps or [],
    )


def test_topological_sort_linear():
    nodes = [
        _node("FR-1"),
        _node("FR-2", deps=["FR-1"]),
        _node("FR-3", deps=["FR-2"]),
    ]
    assert topological_sort(nodes) == ["FR-1", "FR-2", "FR-3"]


def test_topological_sort_cycle_returns_none():
    nodes = [_node("FR-1", deps=["FR-2"]), _node("FR-2", deps=["FR-1"])]
    assert topological_sort(nodes) is None


def test_validate_graph_detects_cycle():
    nodes = [_node("FR-1", deps=["FR-2"]), _node("FR-2", deps=["FR-1"])]
    errors = validate_graph(nodes)
    assert any("순환" in e for e in errors)


def test_validate_graph_detects_dangling_ref():
    nodes = [_node("FR-1", deps=["MISSING"])]
    errors = validate_graph(nodes)
    assert any("존재하지 않는 의존성" in e for e in errors)


def test_validate_graph_detects_duplicate_id():
    nodes = [_node("FR-1"), _node("FR-1")]
    errors = validate_graph(nodes)
    assert any("중복된" in e for e in errors)


def test_validate_graph_clean():
    nodes = [_node("FR-1"), _node("FR-2", deps=["FR-1"])]
    assert validate_graph(nodes) == []


def test_render_mermaid_has_nodes_edges_and_classes():
    graph = RequirementGraph(nodes=[
        _node("FR-1"),
        _node("FR-2", deps=["FR-1"], category="constraint"),
    ])
    mermaid = render_requirement_mermaid(graph)
    assert mermaid.startswith("flowchart TD")
    assert "classDef constraint" in mermaid
    assert "FR-1 --> FR-2" in mermaid
    assert "FR-1: 요구사항 FR-1" in mermaid
    assert ":::constraint" in mermaid


def test_render_mermaid_escapes_quotes():
    graph = RequirementGraph(nodes=[_node("FR-1")])
    graph.nodes[0].title = '제목 "인용" 포함'
    mermaid = render_requirement_mermaid(graph)
    # 큰따옴표는 Mermaid 문법 충돌을 피하려고 작은따옴표로 치환된다.
    assert "제목 '인용' 포함" in mermaid
