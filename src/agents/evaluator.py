"""evaluator.py -- 평가 지표 관점의 Evaluator 역할 에이전트."""

from typing import List

from langchain_openai import ChatOpenAI

from .base import AgentContext, BaseAgent
from documentation_agent.contract_synthesis import (
    critique_contracts_with_llm,
    propose_contracts_with_llm,
)
from documentation_agent.contracts import InterfaceContract

EVALUATOR_SYSTEM_PROMPT = (
    "당신은 RAG 시스템의 품질 평가(recall@k, MRR, 지연시간, 신뢰성)를 담당하는 "
    "Evaluator 역할 전문가입니다. 검색 품질을 정량화·회귀 테스트하기 위한 "
    "평가 하니스 계약을 제안하고 기존 계약을 비판합니다."
)


class EvaluatorAgent(BaseAgent):
    name: str = "RAG Evaluator Agent"
    role: str = "Evaluator"

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def propose_contracts(self, context: AgentContext) -> List[InterfaceContract]:
        return propose_contracts_with_llm(
            self.llm, EVALUATOR_SYSTEM_PROMPT,
            context.user_request, context.existing_contracts,
        )

    def critique_contracts(self, context: AgentContext, contracts: List[InterfaceContract]) -> List[str]:
        return critique_contracts_with_llm(self.llm, EVALUATOR_SYSTEM_PROMPT, contracts)
