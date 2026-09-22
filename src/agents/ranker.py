"""ranker.py -- 재랭킹/다양성 관점의 Ranker 역할 에이전트."""

from typing import List

from langchain_openai import ChatOpenAI

from .base import AgentContext, BaseAgent
from documentation_agent.contract_synthesis import (
    critique_contracts_with_llm,
    propose_contracts_with_llm,
)
from documentation_agent.contracts import InterfaceContract

RANKER_SYSTEM_PROMPT = (
    "당신은 RAG의 랭킹/재랭킹 품질을 담당하는 Ranker 역할 전문가입니다. "
    "검색 결과의 정확도·다양성, RRF 융합 이후의 재랭킹, 상위 k 결과의 중복 제거를 "
    "개선하는 인터페이스 계약을 제안하고 기존 계약을 비판합니다."
)


class RankerAgent(BaseAgent):
    name: str = "RAG Ranker Agent"
    role: str = "Ranker"

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def propose_contracts(self, context: AgentContext) -> List[InterfaceContract]:
        return propose_contracts_with_llm(
            self.llm, RANKER_SYSTEM_PROMPT,
            context.user_request, context.existing_contracts,
        )

    def critique_contracts(self, context: AgentContext, contracts: List[InterfaceContract]) -> List[str]:
        return critique_contracts_with_llm(self.llm, RANKER_SYSTEM_PROMPT, contracts)
