from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .models import Interview


class RequirementsDocumentGenerator:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def run(self, user_request: str, interviews: list[Interview]) -> str:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "당신은 수집한 정보에 기반해 요구사항 문서를 작성하는 전문가입니다.",
                ),
                (
                    "human",
                    "아래 사용자 요청과 여러 페르소나의 인터뷰 결과에 기반해,"
                    "요구사항 문서를 작성해 주세요.\n\n"
                    "사용자 요청: {user_request}\n\n"
                    "인터뷰 결과:\n{interview_results}\n"
                    "요구사항 문서에는 아래 섹션을 포함해 주세요:\n"
                    "1. 프로젝트 개요\n"
                    "2. 주요 기능\n"
                    "3. 비기능 요구사항\n"
                    "4. 제약 조건\n"
                    "5. 대상 사용자\n"
                    "6. 우선순위\n"
                    "7. 리스크와 완화 방안\n\n"
                    "출력은 반드시 한국어로 해 주세요.\n\n요구사항 문서:",
                ),
            ]
        )
        chain = prompt | self.llm | StrOutputParser()
        interview_text = "\n\n".join(
            f"페르소나: {i.persona.name} - {i.persona.background}\n"
            f"질문: {i.question}\n답변: {i.answer}\n"
            for i in interviews
        )
        return chain.invoke({
            "user_request": user_request,
            "interview_results": interview_text,
        })
