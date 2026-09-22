# LangGraph 학습 튜토리얼

LangGraph 의 핵심 개념을 4단계 예시로 익힌다. 실행 가능한 코드는
[`example/langgraph_tutorial.py`](../example/langgraph_tutorial.py) 에 있다.

## 실행

```powershell
# LLM 없이 실행 (1,2,4단계)
python example\langgraph_tutorial.py

# 3단계(LLM 구조화 출력) 포함
python example\langgraph_tutorial.py --with-llm

# 테스트 (결정론적 단계 검증)
.\.venv\Scripts\python.exe -m pytest test\test_langgraph_tutorial.py -q
```

---

## 1단계 — 최소 StateGraph (선형 체인)

가장 단순한 형태: 상태를 정의하고, 노드 함수가 상태 일부를 갱신하며 순서대로 실행된다.

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class GreetState(TypedDict):
    name: str
    greeting: str
    shout: str


def make_greeting(state):
    return {"greeting": f"안녕하세요, {state['name']}님!"}


def shout(state):
    return {"shout": state["greeting"].upper()}


graph = StateGraph(GreetState)
graph.add_node("greet", make_greeting)
graph.add_node("shout", shout)
graph.add_edge(START, "greet")
graph.add_edge("greet", "shout")
graph.add_edge("shout", END)

app = graph.compile()
print(app.invoke({"name": "철수"}))
```

**핵심**: `StateGraph(스키마)` → `add_node(이름, 함수)` → `add_edge` → `compile()` → `invoke(초기state)`.
노드 함수는 **변경할 필드만 dict 로 반환**하면 LangGraph 가 자동 병합한다.

---

## 2단계 — 조건부 엣지로 반복(루프)

coopagent 의 `DocumentationAgent` 가 쓰는 패턴: 조건이 충족될 때까지 반복한다.

```python
from pydantic import BaseModel
from langgraph.graph import StateGraph, END


class CounterState(BaseModel):
    count: int = 0
    is_done: bool = False


def increment(state):
    return {"count": state.count + 1}


def check_done(state):
    return {"is_done": state.count >= 3}


def route(state):
    return "loop" if not state.is_done else "stop"


graph = StateGraph(CounterState)
graph.add_node("increment", increment)
graph.add_node("check_done", check_done)
graph.set_entry_point("increment")
graph.add_edge("increment", "check_done")
graph.add_conditional_edges("check_done", route, {"loop": "increment", "stop": END})

app = graph.compile()
print(app.invoke(CounterState()))  # count=3 에서 종료
```

**핵심**: `add_conditional_edges(노드, 라우팅함수, {반환값: 다음노드})`. 라우팅 함수가
반환한 문자열에 매핑된 노드로 분기한다. 같은 노드로 되돌아가면 **루프**가 된다.

---

## 3단계 — LLM 노드 + 구조화 출력 (실전)

`RequirementGraphBuilder` 가 쓰는 패턴: LLM 출력을 pydantic 으로 강제 구조화한다.

```python
from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END


class Task(BaseModel):
    title: str
    priority: str


class TaskList(BaseModel):
    tasks: List[Task] = Field(default_factory=list)


class PlanState(BaseModel):
    goal: str
    tasks: List[Task] = Field(default_factory=list)


def decompose(state):
    llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
    structured = llm.with_structured_output(TaskList)  # 출력을 TaskList 로 강제
    prompt = ChatPromptTemplate.from_messages([
        ("system", "목표를 작은 작업들로 분해하는 전문가입니다."),
        ("human", "목표: {goal}"),
    ])
    chain = prompt | structured
    return {"tasks": chain.invoke({"goal": state.goal}).tasks}


graph = StateGraph(PlanState)
graph.add_node("decompose", decompose)
graph.set_entry_point("decompose")
graph.add_edge("decompose", END)

app = graph.compile()
for t in app.invoke(PlanState(goal="온라인 서점 만들기"))["tasks"]:
    print(f"- [{t.priority}] {t.title}")
```

**핵심**: `llm.with_structured_output(PydanticModel)` → LLM 이 자유 텍스트 대신
정해진 스키마의 객체를 돌려준다. coopagent 의 `ContractSynthesizer`·역할 에이전트가
전부 이 패턴이다.

---

## 4단계 — 여러 모드로 분기 (다중 조건부 엣지)

```python
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END


class SearchState(BaseModel):
    query: str
    mode: str  # fast | accurate | both
    fast_result: str = ""
    accurate_result: str = ""
    final: str = ""


def fast(state):
    return {"fast_result": f"[빠른검색] {state.query}"}


def accurate(state):
    return {"accurate_result": f"[정밀검색] {state.query}"}


def merge(state):
    return {"final": " + ".join(filter(None, [state.fast_result, state.accurate_result]))}


def route(state):
    return state.mode


graph = StateGraph(SearchState)
graph.add_node("fast", fast)
graph.add_node("accurate", accurate)
graph.add_node("merge", merge)
graph.add_conditional_edges(START, route, {"fast": "fast", "accurate": "accurate", "both": "fast"})
graph.add_conditional_edges("fast", route, {"fast": END, "both": "accurate"})
graph.add_edge("accurate", "merge")
graph.add_edge("merge", END)

app = graph.compile()
print(app.invoke(SearchState(query="RAG란?", mode="both")))
```

**핵심**: `START` 에서도 조건부 분기가 가능하고, 같은 라우팅 함수를 여러 지점에서
재사용할 수 있다.

---

## coopagent 실제 코드 대응표

| 학습 예시 | coopagent 실제 코드 |
|---|---|
| 2단계 (루프) | `src/documentation_agent/workflow.py` — `DocumentationAgent._create_graph()` |
| 3단계 (구조화 출력) | `src/documentation_agent/requirement_graph.py` — `RequirementGraphBuilder._decompose()` |
| 4단계 (다중 분기) | `RequirementGraphBuilder._route_validate`(retry/finalize) |
