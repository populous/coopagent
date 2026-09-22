"""test_agents.py -- 역할 에이전트의 정적 속성/배선 단위 테스트.

LLM 호출 없이 각 에이전트의 name/role, 그리고 propose/critique 가 공통 헬퍼를
올바르게 호출하는지(monkeypatch)를 검증한다.
"""

import pytest

from documentation_agent.contracts import InterfaceContract

from agents.evaluator import EvaluatorAgent
from agents.logger import LoggerAgent
from agents.orchestrator import OrchestratorAgent
from agents.rag_retriever import RetrieverAgent
from agents.ranker import RankerAgent


class _NullLLM:
    pass


def _all_agents():
    llm = _NullLLM()
    return [
        RetrieverAgent(llm),
        RankerAgent(llm),
        OrchestratorAgent(llm),
        EvaluatorAgent(llm),
        LoggerAgent(llm),
    ]


def test_agents_have_distinct_roles():
    agents = _all_agents()
    roles = {a.role for a in agents}
    assert roles == {"Retriever", "Ranker", "Orchestrator", "Evaluator", "Logger"}


def test_agents_expose_name():
    for agent in _all_agents():
        assert agent.name


def test_propose_contracts_delegates_to_helper(monkeypatch):
    import agents.rag_retriever as mod

    sentinel = [InterfaceContract(name="x", role="Retriever")]

    def fake_propose(llm, system_prompt, user_request, existing_contracts):
        return sentinel

    monkeypatch.setattr(mod, "propose_contracts_with_llm", fake_propose)

    agent = RetrieverAgent(_NullLLM())
    from agents.base import AgentContext
    ctx = AgentContext(user_request="RAG", interviews=[], existing_contracts=[])
    assert agent.propose_contracts(ctx) == sentinel


def test_critique_contracts_delegates_to_helper(monkeypatch):
    import agents.rag_retriever as mod

    sentinel = ["리스크", "개선점"]

    def fake_critique(llm, system_prompt, contracts):
        return sentinel

    monkeypatch.setattr(mod, "critique_contracts_with_llm", fake_critique)

    agent = RetrieverAgent(_NullLLM())
    from agents.base import AgentContext
    ctx = AgentContext(user_request="RAG", interviews=[], existing_contracts=[])
    assert agent.critique_contracts(ctx, []) == sentinel
