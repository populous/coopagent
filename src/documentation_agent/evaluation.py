from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .models import EvaluationResult, Interview


class InformationEvaluator:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm.with_structured_output(EvaluationResult)

    def run(self, user_request: str, interviews: list[Interview]) -> EvaluationResult:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "당신은 포괄적인 요구사항 문서 작성을 위한 정보의 충분성을 평가하는 전문가입니다.",
                ),
                (
                    "human",
                    "아래 사용자 요청과 인터뷰 결과에 기반해,"
                    "포괄적인 요구사항 문서를 작성하기에 충분한 정보가 모였는지를"
                    "판단해 주세요.\n\n"
                    "사용자 요청: {user_request}\n\n"
                    "인터뷰 결과:\n{interview_results}",
                ),
            ]
        )
        chain = prompt | self.llm
        interview_text = "\n\n".join(
            f"페르소나: {i.persona.name} - {i.persona.background}\n"
            f"질문: {i.question}\n답변: {i.answer}\n"
            for i in interviews
        )
        return chain.invoke({
            "user_request": user_request,
            "interview_results": interview_text,
        })
