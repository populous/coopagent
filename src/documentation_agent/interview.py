from typing import List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .models import Interview, InterviewResult, Persona


class InterviewConductor:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def run(self, user_request: str, personas: List[Persona]) -> InterviewResult:
        questions = self._generate_questions(user_request=user_request, personas=personas)
        answers = self._generate_answers(personas=personas, questions=questions)
        interviews = self._create_interviews(personas=personas, questions=questions, answers=answers)
        return InterviewResult(interviews=interviews)

    def _generate_questions(self, user_request: str, personas: List[Persona]) -> List[str]:
        question_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "당신은 사용자 요구사항에 기반해 적절한 질문을 생성하는 전문가입니다.",
                ),
                (
                    "human",
                    "아래 페르소나와 관련된 사용자 요청에 대해, 질문 하나를 생성해 주세요.\n\n"
                    "사용자 요청: {user_request}\n"
                    "페르소나: {persona_name} - {persona_background}\n\n"
                    "질문은 구체적이고, 이 페르소나의 관점에서 중요한 정보를 이끌어내도록 설계해 주세요.",
                ),
            ]
        )
        question_chain = question_prompt | self.llm | StrOutputParser()
        question_queries = [
            {
                "user_request": user_request,
                "persona_name": persona.name,
                "persona_background": persona.background,
            }
            for persona in personas
        ]
        return question_chain.batch(question_queries)

    def _generate_answers(self, personas: List[Persona], questions: List[str]) -> List[str]:
        answer_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "당신은 아래 페르소나로서 답변하고 있습니다: {persona_name} - {persona_background}",
                ),
                ("human", "질문: {question}"),
            ]
        )
        answer_chain = answer_prompt | self.llm | StrOutputParser()
        answer_queries = [
            {
                "persona_name": persona.name,
                "persona_background": persona.background,
                "question": question,
            }
            for persona, question in zip(personas, questions)
        ]
        return answer_chain.batch(answer_queries)

    def _create_interviews(
        self,
        personas: List[Persona],
        questions: List[str],
        answers: List[str],
    ) -> List[Interview]:
        return [
            Interview(persona=persona, question=question, answer=answer)
            for persona, question, answer in zip(personas, questions, answers)
        ]
