"""logger.py -- 관찰 가능성/진화 로그 관점의 Logger 역할 에이전트."""

from typing import List

from langchain_openai import ChatOpenAI

from .base import AgentContext, BaseAgent
from documentation_agent.contract_synthesis import (
    critique_contracts_with_llm,
    propose_contracts_with_llm,
)
from documentation_agent.contracts import InterfaceContract

LOGGER_SYSTEM_PROMPT = (
    "당신은 RAG 시스템의 관찰 가능성(실행 이력, 계약 진화 로그, 추적성)을 담당하는 "
    "Logger 역할 전문가입니다. 실행/진화 이력을 남기고 출처를 추적하기 위한 "
    "인터페이스 계약을 제안하고 기존 계약을 비판합니다."
)


class LoggerAgent(BaseAgent):
    name: str = "RAG Logger Agent"
    role: str = "Logger"

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def propose_contracts(self, context: AgentContext) -> List[InterfaceContract]:
        return propose_contracts_with_llm(
            self.llm, LOGGER_SYSTEM_PROMPT,
            context.user_request, context.existing_contracts,
        )

    def critique_contracts(self, context: AgentContext, contracts: List[InterfaceContract]) -> List[str]:
        return critique_contracts_with_llm(self.llm, LOGGER_SYSTEM_PROMPT, contracts)
