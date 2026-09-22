"""상태 모델에 대한 단위 테스트."""

from documentation_agent.models import (
    EvaluationResult,
    Interview,
    InterviewState,
    Persona,
)


def test_persona_model():
    p = Persona(name="backend-dev", background="10년차 백엔드 엔지니어")
    assert p.name == "backend-dev"
    assert p.background == "10년차 백엔드 엔지니어"


def test_interview_model():
    p = Persona(name="qa", background="QA 엔지니어")
    i = Interview(persona=p, question="Q?", answer="A.")
    assert i.persona.name == "qa"
    assert i.question == "Q?"
    assert i.answer == "A."


def test_interview_state_defaults():
    s = InterviewState(user_request="RAG 검색 API를 만들어줘")
    assert s.user_request == "RAG 검색 API를 만들어줘"
    assert s.personas == []
    assert s.interviews == []
    assert s.requirements_doc == ""
    assert s.iteration == 0
    assert s.is_information_sufficient is False


def test_evaluation_result_model():
    e = EvaluationResult(reason="충분함", is_sufficient=True)
    assert e.reason == "충분함"
    assert e.is_sufficient is True
