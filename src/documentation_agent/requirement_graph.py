"""requirement_graph.py -- 요구사항을 그래프로 구조화하는 LangGraph 서브워크플로.

산문 텍스트로만 생성되던 요구사항을, 노드(개별 요구사항)와 엣지(의존관계)로 이루어진
RequirementGraph 로 구조화한다. decompose -> link_dependencies -> validate -> finalize
노드로 구성된 LangGraph StateGraph 다.
"""

from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from .models import Interview, RequirementGraph, RequirementNode

REQUIREMENT_CATEGORIES = ("functional", "non_functional", "constraint", "risk")


class RequirementNodeList(BaseModel):
    """LLM 구조화 출력용: 요구사항 노드 목록 래퍼."""

    nodes: List[RequirementNode] = Field(default_factory=list)


class RequirementGraphState(BaseModel):
    """요구사항 그래프 빌더의 상태."""

    user_request: str
    interviews: List[Interview] = Field(default_factory=list)
    nodes: List[RequirementNode] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    graph: RequirementGraph = Field(default_factory=RequirementGraph)
    iteration: int = 0


def topological_sort(nodes: List[RequirementNode]) -> List[str] | None:
    """Kahn 알고리즘 기반 위상 정렬. 순환이 있으면 None 을 돌려준다."""
    id_set = {n.id for n in nodes}
    indegree = {n.id: 0 for n in nodes}
    adj = {n.id: [] for n in nodes}  # prerequisite -> dependents
    for node in nodes:
        for dep in node.depends_on:
            if dep not in id_set:
                continue  # dangling 참조는 validate 에서 별도 처리
            adj[dep].append(node.id)
            indegree[node.id] += 1

    queue = [nid for nid, deg in indegree.items() if deg == 0]
    order: List[str] = []
    while queue:
        current = queue.pop(0)
        order.append(current)
        for nxt in adj[current]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    if len(order) != len(nodes):
        return None
    return order


def validate_graph(nodes: List[RequirementNode]) -> List[str]:
    """그래프의 구조적 오류(중복 id, 존재하지 않는 의존성, 순환)를 찾는다."""
    errors: List[str] = []
    ids = [n.id for n in nodes]

    seen = set()
    for nid in ids:
        if nid in seen:
            errors.append(f"중복된 요구사항 id: {nid}")
        seen.add(nid)

    id_set = set(ids)
    for node in nodes:
        for dep in node.depends_on:
            if dep not in id_set:
                errors.append(f"{node.id}: 존재하지 않는 의존성 '{dep}' 참조")

    if topological_sort(nodes) is None:
        errors.append("순환 의존성이 존재합니다.")
    return errors


def _interviews_text(interviews: List[Interview]) -> str:
    if not interviews:
        return "(인터뷰 없음)"
    return "\n\n".join(
        f"페르소나: {i.persona.name} - {i.persona.background}\n"
        f"질문: {i.question}\n답변: {i.answer}"
        for i in interviews
    )


def _nodes_text(nodes: List[RequirementNode]) -> str:
    if not nodes:
        return "(없음)"
    return "\n".join(
        f"- {n.id} [{n.category}] {n.title}: {n.description}" for n in nodes
    )

class RequirementGraphBuilder:
    """인터뷰 결과로부터 요구사항 그래프를 생성하는 LangGraph 서브워크플로."""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.graph = self._create_graph()

    def _create_graph(self):
        workflow = StateGraph(RequirementGraphState)
        workflow.add_node("decompose", self._decompose)
        workflow.add_node("link_dependencies", self._link_dependencies)
        workflow.add_node("validate", self._validate)
        workflow.add_node("finalize", self._finalize)

        workflow.set_entry_point("decompose")
        workflow.add_edge("decompose", "link_dependencies")
        workflow.add_edge("link_dependencies", "validate")
        workflow.add_conditional_edges(
            "validate",
            self._route_validate,
            {"finalize": "finalize", "retry": "link_dependencies"},
        )
        workflow.add_edge("finalize", END)
        return workflow.compile()

    def _decompose(self, state: RequirementGraphState) -> dict:
        structured = self.llm.with_structured_output(RequirementNodeList)
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "당신은 요구사항을 개별 요구사항 노드로 분해하는 전문가입니다.",
            ),
            (
                "human",
                "아래 사용자 요청과 인터뷰 결과를 바탕으로, 요구사항을 개별 노드로 분해해 주세요.\n\n"
                "각 노드는 id(FR-1/NFR-1/CON-1/RISK-1 형식), title, description, "
                f"category({', '.join(REQUIREMENT_CATEGORIES)} 중 하나)를 가집니다. "
                "depends_on 은 비워 두세요.\n\n"
                "사용자 요청: {user_request}\n\n인터뷰 결과:\n{interviews}",
            ),
        ])
        chain = prompt | structured
        result = chain.invoke({
            "user_request": state.user_request,
            "interviews": _interviews_text(state.interviews),
        })
        return {"nodes": result.nodes}

    def _link_dependencies(self, state: RequirementGraphState) -> dict:
        if not state.nodes:
            return {"nodes": state.nodes}
        structured = self.llm.with_structured_output(RequirementNodeList)
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "당신은 요구사항 간 의존관계를 식별하는 전문가입니다.",
            ),
            (
                "human",
                "아래 요구사항 노드들에 대해, 각 노드가 의존하는 선행 요구사항 id 들을 "
                "depends_on 에 채워 주세요. 자기 자신이나 존재하지 않는 id 는 참조하지 마세요.\n\n"
                "요구사항:\n{nodes}",
            ),
        ])
        chain = prompt | structured
        result = chain.invoke({"nodes": _nodes_text(state.nodes)})
        return {"nodes": result.nodes}

    def _validate(self, state: RequirementGraphState) -> dict:
        errors = validate_graph(state.nodes)
        return {"validation_errors": errors, "iteration": state.iteration + 1}

    def _route_validate(self, state: RequirementGraphState) -> str:
        if state.validation_errors and state.iteration < 3:
            return "retry"
        return "finalize"

    def _finalize(self, state: RequirementGraphState) -> dict:
        return {"graph": RequirementGraph(nodes=state.nodes)}

    def run(self, user_request: str, interviews: List[Interview]) -> RequirementGraph:
        final = self.graph.invoke(
            RequirementGraphState(user_request=user_request, interviews=interviews)
        )
        return final["graph"]

