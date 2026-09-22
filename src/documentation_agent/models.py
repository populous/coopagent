from typing import Annotated, Any, Optional
import operator
from pydantic import BaseModel, Field


class Persona(BaseModel):
    name: str = Field(..., description="페르소나 이름")
    background: str = Field(..., description="페르소나가 가진 배경")


class Personas(BaseModel):
    personas: list[Persona] = Field(
        default_factory=list, description="페르소나 목록"
    )


class Interview(BaseModel):
    persona: Persona = Field(..., description="인터뷰 대상 페르소나")
    question: str = Field(..., description="인터뷰에서의 질문")
    answer: str = Field(..., description="인터뷰에서의 답변")


class InterviewResult(BaseModel):
    interviews: list[Interview] = Field(
        default_factory=list, description="인터뷰 결과 목록"
    )


class EvaluationResult(BaseModel):
    reason: str = Field(..., description="판단 이유")
    is_sufficient: bool = Field(..., description="정보가 충분한지 여부")


class RequirementNode(BaseModel):
    """요구사항 그래프의 노드 (개별 요구사항)."""

    id: str = Field(..., description="요구사항 식별자 (예: FR-1, NFR-1)")
    title: str = Field(..., description="요구사항 제목")
    description: str = Field(..., description="요구사항 설명")
    category: str = Field(..., description="functional | non_functional | constraint | risk")
    depends_on: list[str] = Field(
        default_factory=list, description="의존하는 선행 요구사항 id 목록"
    )


class RequirementGraph(BaseModel):
    """요구사항 체계 그래프 (노드=요구사항, 엣지=의존관계)."""

    nodes: list[RequirementNode] = Field(default_factory=list)


class InterviewState(BaseModel):
    user_request: str = Field(..., description="사용자 요청")
    personas: Annotated[list[Persona], operator.add] = Field(
        default_factory=list, description="생성된 페르소나 목록"
    )
    interviews: Annotated[list[Interview], operator.add] = Field(
        default_factory=list, description="수행된 인터뷰 목록"
    )
    requirements_doc: str = Field(default="", description="생성된 요구사항 정의")
    requirement_graph: RequirementGraph = Field(
        default_factory=RequirementGraph, description="구조화된 요구사항 그래프"
    )
    requirement_graph_mermaid: str = Field(
        default="", description="요구사항 그래프의 Mermaid 렌더링"
    )
    iteration: int = Field(
        default=0, description="페르소나 생성과 인터뷰 반복 횟수"
    )
    is_information_sufficient: bool = Field(
        default=False, description="정보가 충분한지 여부"
    )
