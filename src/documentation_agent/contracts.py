from typing import List
from pydantic import BaseModel, Field


class InterfaceContract(BaseModel):
    """워크플로를 구성하는 모듈/스텝 간 인터페이스 계약"""

    name: str = Field(..., description="컨트랙트 이름 (모듈/스텝명)")
    role: str = Field(..., description="역할 (Retriever, Ranker, Orchestrator 등)")
    inputs: List[str] = Field(default_factory=list, description="입력 데이터/메시지")
    outputs: List[str] = Field(default_factory=list, description="출력 데이터/메시지")
    preconditions: List[str] = Field(default_factory=list, description="전제 조건/불변량")
    postconditions: List[str] = Field(default_factory=list, description="종료 시 보장되는 상태/불변량")
    failure_modes: List[str] = Field(default_factory=list, description="실패 모드 및 에러 조건")
    metrics: List[str] = Field(default_factory=list, description="관찰/평가에 사용될 지표")
