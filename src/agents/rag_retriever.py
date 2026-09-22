from typing import List

from langchain_openai import ChatOpenAI

from .base import AgentContext, BaseAgent
from documentation_agent.contract_synthesis import (
    critique_contracts_with_llm,
    propose_contracts_with_llm,
)
from documentation_agent.contracts import InterfaceContract

RETRIEVER_SYSTEM_PROMPT = (
    "당신은 RAG 아키텍처의 리트리버 설계(소스/인덱스/리트리벌 규칙, 임베딩 모델 "
    "버전 관리, 청킹)에 정통한 전문가입니다. 검색 단계의 인터페이스 계약을 "
    "제안하고 기존 계약을 비판합니다."
)


class RetrieverAgent(BaseAgent):
    """RAG에서 소스/인덱스/리트리벌 규칙 중심 계약을 제안하는 에이전트"""

    name: str = "RAG Retriever Agent"
    role: str = "Retriever"

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def propose_contracts(self, context: AgentContext) -> List[InterfaceContract]:
        return propose_contracts_with_llm(
            self.llm, RETRIEVER_SYSTEM_PROMPT,
            context.user_request, context.existing_contracts,
        )

    def critique_contracts(self, context: AgentContext, contracts: List[InterfaceContract]) -> List[str]:
        return critique_contracts_with_llm(self.llm, RETRIEVER_SYSTEM_PROMPT, contracts)
