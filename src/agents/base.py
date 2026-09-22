from typing import Protocol, List
from pydantic import BaseModel

from documentation_agent.contracts import InterfaceContract


class AgentContext(BaseModel):
    """에이전트가 계약을 제안/비판할 때 사용하는 공통 컨텍스트"""

    user_request: str
    interviews: List[object] = []  # 필요 시 Interview로 좁힐 수 있음
    existing_contracts: List[InterfaceContract] = []


class BaseAgent(Protocol):
    """역할 기반 멀티 에이전트 공통 인터페이스"""

    name: str
    role: str

    def propose_contracts(self, context: AgentContext) -> List[InterfaceContract]:
        """에이전트 관점에서 새로운/수정된 컨트랙트 제안"""
        ...

    def critique_contracts(self, context: AgentContext, contracts: List[InterfaceContract]) -> List[str]:
        """컨트랙트에 대한 비판/리스크/보완점 피드백"""
        ...
