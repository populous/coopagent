"""example/langgraph_tutorial.py -- LangGraph 학습용 예시 코드.

4단계로 LangGraph 의 핵심 개념을 익힌다:
  1) 최소 StateGraph (선형 체인)
  2) 조건부 엣지로 반복(루프)
  3) LLM 노드 + 구조화 출력 (실전, OPENAI_API_KEY 필요)
  4) 여러 모드로 분기 (다중 조건부 엣지)

실행:
    python example/langgraph_tutorial.py             # 1,2,4단계 (LLM 없음)
    python example/langgraph_tutorial.py --with-llm  # 3단계 포함 (API 키 필요)

학습 포인트:
  - StateGraph(스키마) -> add_node(이름, 함수) -> add_edge/conditional_edges -> compile()
  - 노드 함수는 "변경할 필드만" dict 로 반환하면 LangGraph 가 자동 병합한다.
"""

from typing import List, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1단계: 최소 StateGraph (선형 체인)
# ---------------------------------------------------------------------------

class GreetState(TypedDict):
    name: str
    greeting: str
    shout: str


def _make_greeting(state: GreetState) -> dict:
    return {"greeting": f"안녕하세요, {state['name']}님!"}


def _shout(state: GreetState) -> dict:
    return {"shout": state["greeting"].upper()}


def build_greet_graph():
    """name -> greeting -> shout 순으로 실행되는 가장 단순한 그래프."""
    graph = StateGraph(GreetState)
    graph.add_node("greet", _make_greeting)
    graph.add_node("shout", _shout)
    graph.add_edge(START, "greet")
    graph.add_edge("greet", "shout")
    graph.add_edge("shout", END)
    return graph.compile()


# ---------------------------------------------------------------------------
# 2단계: 조건부 엣지로 반복(루프)
# ---------------------------------------------------------------------------

class CounterState(BaseModel):
    count: int = 0
    is_done: bool = False


def _increment(state: CounterState) -> dict:
    return {"count": state.count + 1}


def _check_done(state: CounterState) -> dict:
    return {"is_done": state.count >= 3}


def _route(state: CounterState) -> str:
    return "loop" if not state.is_done else "stop"


def build_counter_graph():
    """count 가 3 이 될 때까지 increment 를 반복하는 그래프."""
    graph = StateGraph(CounterState)
    graph.add_node("increment", _increment)
    graph.add_node("check_done", _check_done)
    graph.set_entry_point("increment")
    graph.add_edge("increment", "check_done")
    graph.add_conditional_edges(
        "check_done", _route,
        {"loop": "increment", "stop": END},
    )
    return graph.compile()

# ---------------------------------------------------------------------------
# 3단계: LLM 노드 + 구조화 출력 (실전)
# ---------------------------------------------------------------------------

class Task(BaseModel):
    title: str
    priority: str  # "high" | "medium" | "low"


class TaskList(BaseModel):
    tasks: List[Task] = Field(default_factory=list)


class PlanState(BaseModel):
    goal: str
    tasks: List[Task] = Field(default_factory=list)


def _decompose(state: PlanState) -> dict:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
    structured = llm.with_structured_output(TaskList)  # 출력을 TaskList 로 강제
    prompt = ChatPromptTemplate.from_messages([
        ("system", "목표를 작은 작업(task)들로 분해하는 전문가입니다."),
        ("human", "목표: {goal}\n각 작업에 title과 priority(high/medium/low)를 부여하세요."),
    ])
    chain = prompt | structured
    result: TaskList = chain.invoke({"goal": state.goal})
    return {"tasks": result.tasks}


def build_plan_graph():
    """LLM 이 목표를 구조화된 Task 목록으로 분해하는 그래프."""
    graph = StateGraph(PlanState)
    graph.add_node("decompose", _decompose)
    graph.set_entry_point("decompose")
    graph.add_edge("decompose", END)
    return graph.compile()


# ---------------------------------------------------------------------------
# 4단계: 여러 모드로 분기 (다중 조건부 엣지)
# ---------------------------------------------------------------------------

class SearchState(BaseModel):
    query: str
    mode: str  # "fast" | "accurate" | "both"
    fast_result: str = ""
    accurate_result: str = ""
    final: str = ""


def _fast_search(state: SearchState) -> dict:
    return {"fast_result": f"[빠른검색] {state.query}"}


def _accurate_search(state: SearchState) -> dict:
    return {"accurate_result": f"[정밀검색] {state.query}"}


def _merge(state: SearchState) -> dict:
    combined = " + ".join(filter(None, [state.fast_result, state.accurate_result]))
    return {"final": combined}


def _route_by_mode(state: SearchState) -> str:
    return state.mode


def build_search_graph():
    """mode 에 따라 fast/accurate/both 로 분기하는 그래프."""
    graph = StateGraph(SearchState)
    graph.add_node("fast", _fast_search)
    graph.add_node("accurate", _accurate_search)
    graph.add_node("merge", _merge)

    # START 에서 모드에 따라 분기
    graph.add_conditional_edges(START, _route_by_mode, {
        "fast": "fast",
        "accurate": "accurate",
        "both": "fast",
    })
    # fast 이후: fast 모드면 종료, both 면 accurate 로
    graph.add_conditional_edges("fast", _route_by_mode, {
        "fast": END,
        "both": "accurate",
    })
    graph.add_edge("accurate", "merge")
    graph.add_edge("merge", END)
    return graph.compile()


# ---------------------------------------------------------------------------
# 실행
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="LangGraph 학습용 예시")
    parser.add_argument("--with-llm", action="store_true",
                        help="3단계(LLM 구조화 출력) 포함 실행")
    args = parser.parse_args()

    print("=== 1단계: 선형 체인 ===")
    print(build_greet_graph().invoke({"name": "철수"}))

    print("\n=== 2단계: 조건부 루프 ===")
    print(build_counter_graph().invoke(CounterState()))

    if args.with_llm:
        print("\n=== 3단계: LLM 구조화 출력 ===")
        final = build_plan_graph().invoke(PlanState(goal="온라인 서점 만들기"))
        for task in final["tasks"]:
            print(f"- [{task.priority}] {task.title}")
    else:
        print("\n=== 3단계: LLM 구조화 출력 (건너뜀, --with-llm 필요) ===")

    print("\n=== 4단계: 다중 모드 분기 ===")
    print(build_search_graph().invoke(SearchState(query="RAG란?", mode="both")))


if __name__ == "__main__":
    main()

