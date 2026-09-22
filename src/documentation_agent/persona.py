from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .models import Personas


class PersonaGenerator:
    def __init__(self, llm: ChatOpenAI, k: int = 5):
        # LLM을 Personas 구조체 출력으로 래핑
        self.llm = llm.with_structured_output(Personas)
        self.k = k

    def run(self, user_request: str) -> Personas:
        """사용자 요청에 대해 k명의 페르소나를 생성한다"""
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "당신은 사용자 인터뷰용 다양한 페르소나를 만드는 전문가입니다.",
                ),
                (
                    "human",
                    "아래 사용자 요청에 관한 인터뷰용으로,"
                    f"{self.k}명의 다양한 페르소나를 생성해 주세요.\n\n"
                    "사용자 요청: {user_request}\n\n"
                    "각 페르소나에는 이름과 간단한 배경을 포함해 주세요."
                    "연령, 성별, 직업, 기술적 전문 지식에서 다양성을 확보해 주세요.",
                ),
            ]
        )
        chain = prompt | self.llm
        return chain.invoke({"user_request": user_request})
