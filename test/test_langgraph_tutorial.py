"""test_langgraph_tutorial.py -- 튜토리얼의 결정론적 단계(1,2,4) 검증.

LLM 없이 실행 가능한 그래프만 검증한다.
"""

from example.langgraph_tutorial import (
    CounterState,
    SearchState,
    build_counter_graph,
    build_greet_graph,
    build_search_graph,
)


def test_greet_graph_linear_chain():
    result = build_greet_graph().invoke({"name": "철수"})
    assert result["greeting"] == "안녕하세요, 철수님!"
    assert result["shout"] == "안녕하세요, 철수님!".upper()


def test_counter_graph_loops_until_done():
    final = build_counter_graph().invoke(CounterState())
    assert final["count"] == 3
    assert final["is_done"] is True


def test_search_graph_both_mode_merges():
    final = build_search_graph().invoke(SearchState(query="RAG", mode="both"))
    assert "[빠른검색] RAG" in final["final"]
    assert "[정밀검색] RAG" in final["final"]


def test_search_graph_fast_mode_short_circuits():
    final = build_search_graph().invoke(SearchState(query="RAG", mode="fast"))
    # fast 모드에서는 merge 를 거치지 않으므로 final 은 비어 있다.
    assert final["final"] == ""
    assert final["fast_result"] == "[빠른검색] RAG"
