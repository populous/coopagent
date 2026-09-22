"""InterfaceContract 모델에 대한 단위 테스트."""

import pytest
from pydantic import ValidationError

from documentation_agent.contracts import InterfaceContract


def test_contract_defaults_are_empty_lists():
    c = InterfaceContract(name="retrieve", role="Retriever")
    assert c.name == "retrieve"
    assert c.role == "Retriever"
    assert c.inputs == []
    assert c.outputs == []
    assert c.preconditions == []
    assert c.postconditions == []
    assert c.failure_modes == []
    assert c.metrics == []


def test_contract_holds_full_fields():
    c = InterfaceContract(
        name="answer",
        role="AnswerSynthesizer",
        inputs=["context", "question"],
        outputs=["answer"],
        preconditions=["context must not be empty"],
        postconditions=["answer is grounded in context"],
        failure_modes=["no relevant context"],
        metrics=["latency_ms", "faithfulness"],
    )
    assert c.inputs == ["context", "question"]
    assert c.outputs == ["answer"]
    assert c.preconditions == ["context must not be empty"]
    assert c.postconditions == ["answer is grounded in context"]
    assert c.failure_modes == ["no relevant context"]
    assert c.metrics == ["latency_ms", "faithfulness"]


def test_contract_name_and_role_are_required():
    with pytest.raises(ValidationError):
        InterfaceContract()
