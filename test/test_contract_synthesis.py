"""test_contract_synthesis.py -- 계약 합성/포맷팅 단위 테스트.

LLM 호출 없이 결정론적으로 검증할 수 있는 부분(포맷터, 래퍼 모델, 합성기 배선)을
검증한다.
"""

from documentation_agent.contract_synthesis import (
    ContractList,
    ContractSynthesizer,
    CritiqueList,
    format_contracts,
    format_interviews,
)
from documentation_agent.contracts import InterfaceContract
from documentation_agent.models import Interview, Persona


def _interviews():
    p = Persona(name="retriever-dev", background="검색 엔지니어")
    return [
        Interview(persona=p, question="검색 품질은?", answer="재랭킹이 필요합니다."),
        Interview(persona=p, question="평가는?", answer="recall@k로 측정해야 합니다."),
    ]


def _contract():
    return InterfaceContract(
        name="retriever",
        role="Retriever",
        inputs=["query"],
        outputs=["docs"],
        preconditions=["index ready"],
        postconditions=["top-k returned"],
    )


def test_format_interviews_contains_qa():
    text = format_interviews(_interviews())
    assert "재랭킹이 필요합니다." in text
    assert "retriever-dev" in text


def test_format_interviews_empty():
    assert format_interviews([]) == "(인터뷰 없음)"


def test_format_contracts_contains_fields():
    text = format_contracts([_contract()])
    assert "retriever" in text
    assert "role=Retriever" in text
    assert "query" in text


def test_format_contracts_empty():
    assert format_contracts([]) == "(없음)"


def test_contract_list_wrapper():
    cl = ContractList(contracts=[_contract()])
    assert len(cl.contracts) == 1
    assert cl.contracts[0].name == "retriever"


def test_critique_list_wrapper():
    cr = CritiqueList(critiques=["리스크: 지연시간", "개선: 재랭킹"])
    assert cr.critiques == ["리스크: 지연시간", "개선: 재랭킹"]


class _FakeRunnable:
    def __init__(self, result):
        self._result = result

    def __call__(self, _input):
        return self._result


class _FakeLLM:
    """with_structured_output 만 구현한 가짜 LLM."""

    def __init__(self, result):
        self._result = result

    def with_structured_output(self, schema):
        return _FakeRunnable(self._result)


def test_contract_synthesizer_returns_llm_result():
    expected = ContractList(contracts=[_contract()])
    synth = ContractSynthesizer(_FakeLLM(expected))
    result = synth.run("RAG 구축", _interviews())
    assert len(result) == 1
    assert result[0].name == "retriever"
