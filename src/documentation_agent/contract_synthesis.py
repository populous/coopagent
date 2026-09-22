"""contract_synthesis.py -- 인터뷰 결과를 InterfaceContract 세트로 자동 합성한다.

이슈 #1 목표 1의 ContractSynthesizer 구현이다. 페르소나 인터뷰 결과(InterviewResult)를
받아 LLM 구조화 출력으로 인터페이스 계약 목록을 생성한다. 역할 에이전트(agents/)가
계약을 제안/비판할 때 공통으로 쓰는 헬퍼도 여기에 둔다.
"""

from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .contracts import InterfaceContract
from .models import Interview


class ContractList(BaseModel):
    """LLM 구조화 출력용: 계약 목록 래퍼."""

    contracts: List[InterfaceContract] = Field(default_factory=list)


class CritiqueList(BaseModel):
    """LLM 구조화 출력용: 비판 문구 목록 래퍼."""

    critiques: List[str] = Field(default_factory=list)


def format_interviews(interviews: List[Interview]) -> str:
    """인터뷰 목록을 프롬프트에 넣을 텍스트로 변환한다."""
    if not interviews:
        return "(인터뷰 없음)"
    return "\n\n".join(
        f"페르소나: {i.persona.name} - {i.persona.background}\n"
        f"질문: {i.question}\n"
        f"답변: {i.answer}"
        for i in interviews
    )


def format_contracts(contracts: List[InterfaceContract]) -> str:
    """계약 목록을 프롬프트에 넣을 텍스트로 변환한다."""
    if not contracts:
        return "(없음)"
    lines: List[str] = []
    for c in contracts:
        lines.append(
            f"- {c.name} (role={c.role})\n"
            f"  inputs={c.inputs}\n"
            f"  outputs={c.outputs}\n"
            f"  preconditions={c.preconditions}\n"
            f"  postconditions={c.postconditions}\n"
            f"  failure_modes={c.failure_modes}\n"
            f"  metrics={c.metrics}"
        )
    return "\n".join(lines)


class ContractSynthesizer:
    """인터뷰 결과로부터 인터페이스 계약을 자동 합성한다."""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm.with_structured_output(ContractList)

    def run(self, user_request: str, interviews: List[Interview]) -> List[InterfaceContract]:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "당신은 워크플로를 구성하는 모듈/스텝 간 인터페이스 계약을 정의하는 전문가입니다.",
                ),
                (
                    "human",
                    "아래 사용자 요청과 페르소나 인터뷰 결과를 바탕으로 필요한 인터페이스 "
                    "계약들을 제안해 주세요.\n\n"
                    "각 계약은 name, role, inputs, outputs, preconditions, postconditions, "
                    "failure_modes, metrics 필드를 가집니다.\n\n"
                    "사용자 요청: {user_request}\n\n"
                    "인터뷰 결과:\n{interviews}",
                ),
            ]
        )
        chain = prompt | self.llm
        result = chain.invoke({
            "user_request": user_request,
            "interviews": format_interviews(interviews),
        })
        return result.contracts


def propose_contracts_with_llm(
    llm: ChatOpenAI,
    system_prompt: str,
    user_request: str,
    existing_contracts: List[InterfaceContract],
) -> List[InterfaceContract]:
    """역할 에이전트 공통: LLM에게 계약 제안을 요청해 파싱한다."""
    structured = llm.with_structured_output(ContractList)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                "사용자 요청: {user_request}\n\n"
                "기존 계약:\n{contracts}\n\n"
                "이 요청을 만족하는 데 필요한 인터페이스 계약들을 제안해 주세요. "
                "각 계약은 name, role, inputs, outputs, preconditions, postconditions, "
                "failure_modes, metrics 필드를 가집니다.",
            ),
        ]
    )
    chain = prompt | structured
    result = chain.invoke({
        "user_request": user_request,
        "contracts": format_contracts(existing_contracts),
    })
    return result.contracts


def critique_contracts_with_llm(
    llm: ChatOpenAI,
    system_prompt: str,
    contracts: List[InterfaceContract],
) -> List[str]:
    """역할 에이전트 공통: LLM에게 계약 비판을 요청해 문자열 목록으로 받는다."""
    structured = llm.with_structured_output(CritiqueList)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                "아래 인터페이스 계약들을 검토하고, 주요 리스크·보완점·개선점을 "
                "문자열 목록으로 제시해 주세요.\n\n계약:\n{contracts}",
            ),
        ]
    )
    chain = prompt | structured
    result = chain.invoke({"contracts": format_contracts(contracts)})
    return result.critiques
