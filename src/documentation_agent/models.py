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


class InterviewState(BaseModel):
    user_request: str = Field(..., description="사용자 요청")
    personas: Annotated[list[Persona], operator.add] = Field(
        default_factory=list, description="생성된 페르소나 목록"
    )
    interviews: Annotated[list[Interview], operator.add] = Field(
        default_factory=list, description="수행된 인터뷰 목록"
    )
    requirements_doc: str = Field(default="", description="생성된 요구사항 정의")
    iteration: int = Field(
        default=0, description="페르소나 생성과 인터뷰 반복 횟수"
    )
    is_information_sufficient: bool = Field(
        default=False, description="정보가 충분한지 여부"
    )
