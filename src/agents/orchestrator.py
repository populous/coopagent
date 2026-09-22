"""orchestrator.py -- 오케스트레이션 관점의 Orchestrator 역할 에이전트."""

from typing import List

from langchain_openai import ChatOpenAI

from .base import AgentContext, BaseAgent
from documentation_agent.contract_synthesis import (
    critique_contracts_with_llm,
    propose_contracts_with_llm,
)
from documentation_agent.contracts import InterfaceContract

ORCHESTRATOR_SYSTEM_PROMPT = (
    "당신은 RAG 검색 파이프라인의 오케스트레이션(LangGraph 모드 분기, 재시도, "
    "오류 처리, 병렬화)을 담당하는 Orchestrator 역할 전문가입니다. "
    "모드 라우팅·상태 관리·실패 복구를 강화하는 인터페이스 계약을 제안하고 "
    "기존 계약을 비판합니다."
)


class OrchestratorAgent(BaseAgent):
    name: str = "RAG Orchestrator Agent"
    role: str = "Orchestrator"

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def propose_contracts(self, context: AgentContext) -> List[InterfaceContract]:
        return propose_contracts_with_llm(
            self.llm, ORCHESTRATOR_SYSTEM_PROMPT,
            context.user_request, context.existing_contracts,
        )

    def critique_contracts(self, context: AgentContext, contracts: List[InterfaceContract]) -> List[str]:
        return critique_contracts_with_llm(self.llm, ORCHESTRATOR_SYSTEM_PROMPT, contracts)
