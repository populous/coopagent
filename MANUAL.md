# coopagent 사용 매뉴얼

coopagent 는 LangGraph 기반의 **페르소나-인터뷰 요구사항 생성 에이전트**다. 자연어
요구를 인터페이스 계약(`InterfaceContract`)으로 구조화하고, 역할 기반 멀티 에이전트가
계약을 제안·비판·진화시켜 RAG 등 시스템의 워크플로 명세를 만들어낸다.

이 문서는 설치부터 실행·테스트·구조·트러블슈팅까지 사용자 관점에서 전부 기록한 매뉴얼이다.

> GitHub Codespaces(Linux) 에서 실행하는 단계별 안내는 **[CODESPACES.md](CODESPACES.md)** 참고.

---

## 1. 요구 사항

- Python 3.11 이상 (검증: 3.13.5)
- Windows PowerShell (런처 스크립트 기준)
- OpenAI API 키

---

## 2. 환경 설정

### 2.1 원클릭 셋업

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

`setup.ps1` 이 수행하는 일:

1. `.venv` 가상환경 생성 (없으면)
2. `requirements.txt` + `requirements-dev.txt` 의존성 설치
3. `.env` 파일과 `OPENAI_API_KEY` 존재 확인

### 2.2 API 키 설정 (`.env`)

프로젝트 루트의 `.env` 파일에 다음 형식으로 키를 넣는다 (git 에는 커밋되지 않음):

```
OPENAI_API_KEY=sk-...
```

> `.env` 가 없거나 `OPENAI_API_KEY=` 줄이 없으면 LLM 호출이 실패한다.

### 2.3 의존성

| 파일 | 내용 |
|---|---|
| `requirements.txt` | 런타임: `langchain-openai`, `langgraph`, `pydantic`, `python-dotenv`, `PyYAML` (및 전이 의존성) |
| `requirements-dev.txt` | 테스트: `pytest` |

---

## 3. 실행 (런처)

`.venv` 를 자동으로 찾아 `PYTHONPATH=src` 를 주입하고 CLI 를 실행하는 런처를 제공한다.
PowerShell 은 `.ps1`, cmd 는 `.cmd` 를 쓴다.

### 3.1 요구사항 문서 생성 (`documentagent`)

```powershell
.\documentagent.ps1 "만들고 싶은 시스템 설명"          # 페르소나 인터뷰 → 요구사항 문서
.\documentagent.ps1 --task "..." --k 3                # 페르소나 수 지정
.\documentagent.ps1 --task "..." --graph              # 요구사항을 그래프로 구조화 (Mermaid)
```

`--graph` 를 붙이면 요구사항을 개별 노드(기능/비기능/제약/리스크)와 의존관계
엣지로 구조화한 **요구사항 그래프**를 LangGraph 서브워크플로(`decompose → link →
validate`)로 생성하고, Mermaid 로 렌더링해 `docs/requirements_graph.md` 에 저장한다.

### 3.2 RAG 계약 제안 생성 (`ragproposal`)

```powershell
.\ragproposal.ps1 --task "RAG 시스템 구축 요청" --out docs   # 인터뷰 → 계약 합성 → 멀티 에이전트 제안/비판 → YAML
.\ragproposal.ps1 --task "..." --fresh                      # 이전 기록 무시하고 새로 시작
```

### 3.3 공통 옵션

| 옵션 | 설명 |
|---|---|
| `--task TASK` | 입력 요청. **생략하면 대화형으로 입력받는다** |
| `--k N` | 생성할 페르소나 수 (기본 5) |
| `--out DIR` | `ragproposal` 전용: 결과 저장 디렉터리 (기본 `docs`) |
| `--fresh` | `ragproposal` 전용: 이전 기록(`rag_state.json`)을 무시하고 새로 시작 |
| `--graph` | `documentagent` 전용: 요구사항을 그래프로 구조화해 Mermaid 로 출력·저장 |
| `-h` / `--help` | 도움말 |

---

## 4. 프로젝트 구조

```
coopagent/
├── src/
│   ├── documentation_agent/     # 페르소나-인터뷰 + 계약 합성/진화 파이프라인
│   │   ├── models.py            # 상태 모델 (Persona/Interview/InterviewState 등)
│   │   ├── persona.py           # 페르소나 생성
│   │   ├── interview.py         # 인터뷰 진행
│   │   ├── evaluation.py        # 정보 충분성 평가
│   │   ├── requirements.py      # 요구사항 문서 생성
│   │   ├── workflow.py          # LangGraph 기반 DocumentationAgent
│   │   ├── contracts.py         # InterfaceContract 스키마
│   │   ├── syntax.py            # YAML 직렬화 백엔드
│   │   ├── contract_synthesis.py# ContractSynthesizer + 에이전트 공통 헬퍼
│   │   ├── evolution.py         # 병합/충돌/불변조건 검증 + 진화 로그
│   │   ├── requirement_graph.py # 요구사항 그래프 빌더 (LangGraph 서브워크플로)
│   │   ├── rag_proposal.py      # RAG 계약 제안 드라이버 (상태 저장/복원 포함)
│   │   ├── mcp_server.py        # MCP 서버 (OpenCode/Cline 노출)
│   │   ├── mcp_registry.py      # MCP 등록 유틸 (--mcp-*)
│   │   └── cli.py               # documentagent CLI
│   ├── agents/                  # 역할 에이전트
│   │   ├── base.py              # AgentContext, BaseAgent(Protocol)
│   │   ├── rag_retriever.py     # RetrieverAgent
│   │   ├── ranker.py            # RankerAgent
│   │   ├── orchestrator.py      # OrchestratorAgent
│   │   ├── evaluator.py         # EvaluatorAgent
│   │   └── logger.py            # LoggerAgent
│   └── rag/                     # 제안된 RAG 계약의 실행 코드
│       ├── evaluator.py         # recall@k, MRR, latency
│       ├── reranker.py          # MMR 재랭킹, 중복 제거
│       └── provenance.py        # 출처 추적
├── test/                        # pytest 단위 테스트
├── docs/                        # 생성 산출물 + 분석 문서
├── setup.ps1                    # 원클릭 셋업
├── documentagent.ps1 / .cmd     # 런처
├── ragproposal.ps1 / .cmd       # 런처
├── coopagent-mcp.ps1 / .cmd     # MCP 서버 런처
├── CMakeLists.txt               # CTest/CPack 래핑
├── pyproject.toml               # Poetry 메타데이터 + 스크립트
├── requirements.txt             # 런타임 의존성
└── requirements-dev.txt         # 테스트 의존성
```

---

## 5. 동작 원리 (`ragproposal` 파이프라인)

`ragproposal` 은 다음 순서로 coopagent 자체 파이프라인을 실행한다:

1. **페르소나 인터뷰** — `DocumentationAgent` 가 페르소나 생성 → 인터뷰 → 정보 충분성 평가 → 요구사항 문서 생성 (LangGraph 워크플로)
2. **계약 합성** — `ContractSynthesizer` 가 인터뷰 결과로부터 baseline 인터페이스 계약을 합성
3. **멀티 에이전트 제안/비판** — Retriever/Ranker/Orchestrator/Evaluator/Logger 가 각각 `propose_contracts` 와 `critique_contracts` 를 실행
4. **병합/판정** — 계약 병합 + 이름 충돌 검출 + 불변조건(입출력·전후조건) 검증
5. **진화 로그** — 계약의 추가/삭제/강화 이력을 반복별로 기록
6. **YAML 직렬화** — 최종 계약 세트를 YAML 로 렌더링

> **상태 연속성**: `docs/rag_state.json` 이 있으면 3단계의 시작 계약 세트를 새로
> 합성한 baseline 대신 **이전 최종 계약**으로 두고, 그 위에서 에이전트가 다시
> 제안/비판한다. 진화 로그도 이어서 누적된다. `--fresh` 로 무시할 수 있다.

---

## 6. RAG 특화 실행 코드 (`src/rag/`)

`propose_rag_contracts` 가 제안한 계약 중, 외부 서비스 없이 결정론적으로 구현할 수
있는 것들을 실제 파이썬 코드로 구현했다. 임베딩 재호출 없이 순수 계산만 한다.

### 6.1 검색 품질 평가 (`rag/evaluator.py`)

`RankingQualityEvaluator` 계약 구현체. recall@k·MRR·지연시간을 계산한다.

```python
from rag.evaluator import recall_at_k, mrr, latency_ms

recall_at_k(["a", "b"], ["a", "c", "d"], k=2)  # 0.5 (a 만 정답)
mrr(["a"], ["b", "a"])                          # 0.5 (2등에서 첫 정답)
latency_ms(1.5)                                 # 1500.0
```

| 함수 | 설명 |
|---|---|
| `recall_at_k(gt, retrieved, k)` | ground_truth 중 상위 k 에 포함된 비율 |
| `mrr(gt, retrieved)` | 첫 정답의 역순위 (없으면 0.0) |
| `latency_ms(seconds)` | 초 → 밀리초 환산 |

### 6.2 다양성 재랭킹·중복 제거 (`rag/reranker.py`)

`HybridRetrievalEnhancer` 계약 구현체. MMR 로 다양성을 보장하고 Jaccard 로 근접
중복을 제거한다.

```python
from rag.reranker import mmr_rerank, deduplicate

mmr_rerank(["doc a", "doc b", "doc c"], top_k=2)             # 관련성·다양성 절충 재정렬
deduplicate(["foo bar", "foo bar baz", "unrelated"], 0.6)    # 근접 중복 제거
```

| 함수 | 설명 |
|---|---|
| `mmr_rerank(hits, top_k, lambda_)` | Maximal Marginal Relevance 재랭킹 (lambda_ 가 클수록 관련성 우선) |
| `deduplicate(hits, threshold)` | Jaccard 유사도가 threshold 이상인 근접 중복 제거 |

### 6.3 출처 추적 (`rag/provenance.py`)

`Logger` 계약 구현체. 검색 결과에 출처 메타데이터를 부착하고 중복 출처를 정리한다.

```python
from rag.provenance import attach_provenance, unique_sources

attach_provenance([{"text": "hi"}], source="doc.md")          # source/chunk_index 부착
unique_sources([{"source": "a.md"}, {"source": "a.md"}])      # ["a.md"]
```

| 함수 | 설명 |
|---|---|
| `attach_provenance(hits, source)` | 각 hit 에 출처·청크 인덱스 부착 |
| `unique_sources(hits)` | 중복 없이 출처 목록 반환 |

> 이 모듈들은 모두 외부 서비스(Ollama/OpenAI) 없이 결정론적으로 동작하며,
> `test/test_rag.py` 로 검증된다.

---

## 7. 생성 산출물 (`docs/`)

| 파일 | 내용 |
|---|---|
| `rag_proposal.requirements.md` | 페르소나 인터뷰로 생성된 요구사항 문서 |
| `rag_proposal.generated.yaml` | 최종 인터페이스 계약 (YAML) |
| `rag_proposal.summary.json` | 에이전트 비판·진화 로그·충돌/불변조건 검증 결과 |
| `rag_state.json` | 상태 기록: 최종 계약 + 진화 로그 (다음 호출의 입력으로 재사용) |
| `rag_proposal.md` | 실사례 vs 생성 계약 비교·분석 문서 |

---

## 8. 테스트

```powershell
.\.venv\Scripts\python.exe -m pytest test -q                    # pytest (50 tests)
cmake -S . -B build                                              # CMake 구성
ctest --test-dir build -C Release --output-on-failure            # CTest 래핑
cmake --build build --target package --config Release            # CPack 패키징(ZIP/TGZ)
```

> Windows + Visual Studio 멀티컨피그 생성기에서는 `ctest`/`package` 에 `-C Release`(또는 `Debug`) 를 붙여야 한다.

### CMake 프리셋 (`CMakePresets.json`)

프리셋으로 위 절차를 간소화할 수 있다:

```powershell
cmake --list-presets           # 프리셋 목록 확인
cmake --preset default         # 구성 (build/ 에 .venv Python 사용)
cmake --build --preset default # 빌드
ctest --preset default         # 테스트
cpack --preset default         # 패키징 (ZIP/TGZ)

cmake --preset ci              # CI 프리셋 (build-ci/ 사용)
ctest --preset ci
```

| 프리셋 | 용도 |
|---|---|
| `default` | 일반 개발 (VS 18 2026 x64, `build/`) |
| `ci` | 비대화형 CI (별도 `build-ci/`, 실패 시 즉시 중단) |

---

## 9. 트러블슈팅

| 증상 | 원인/해결 |
|---|---|
| `Virtual environment not found` | `.\setup.ps1` 를 먼저 실행해 `.venv` 생성 |
| LLM 호출 시 인증 오류 | `.env` 에 `OPENAI_API_KEY=sk-...` 가 있는지 확인 |
| `.env` 가 있어도 키 인식 안 됨 | `OPENAI_API_KEY=` 접두어가 빠졌는지 확인 |
| `ModuleNotFoundError: documentation_agent` | 런처를 쓰지 않았다면 `PYTHONPATH=src` 필요 |
| `--task` 없이 실행했을 때 | 대화형 프롬프트가 뜨므로 입력 (또는 `--task` 사용) |

---

## 10. 보안 참고

- `.env` 는 `.gitignore` 에 등록되어 git 에 커밋되지 않는다.
- API 키는 코드에 하드코딩하지 않고 `load_dotenv()` 로만 읽는다.
- 키가 외부에 노출된 적이 있다면 **키 회전(재발급)**을 권장한다.

---

## 11. MCP 서버로 노출 (OpenCode/Cline 연동)

coopagent 를 OpenCode/Cline 의 TUI 에서 직접 호출할 수 있도록 MCP 서버를 제공한다.
서버는 stdio 기반 JSON-RPC 로, 도구 4개를 노출한다.

| 도구 | 설명 | 유형 |
|---|---|---|
| `generate_requirements` | 페르소나 인터뷰 → 요구사항 문서 | 읽기 (LLM) |
| `propose_rag_contracts` | 계약 합성 → 멀티 에이전트 제안/비판 → YAML | **쓰기** (LLM) |
| `list_generated_proposals` | 생성된 산출물 목록 | 읽기 |
| `get_proposal_contracts` | 산출물 파일 내용 | 읽기 |

> Cline/OpenCode 각각의 자세한 등록 절차·스키마 차이는 **[MCP_REGISTRATION.md](MCP_REGISTRATION.md)** 참고.

### 등록

```powershell
.\documentagent.ps1 --mcp-print                          # 등록용 JSON 조각 출력
.\documentagent.ps1 --mcp-install --mcp-target opencode  # OpenCode 자동 등록
.\documentagent.ps1 --mcp-install --force                # Cline 덮어쓰기 등록
.\documentagent.ps1 --mcp-status --mcp-target opencode   # 등록 확인
```

### 서버 직접 실행

```powershell
.\coopagent-mcp.ps1    # stdio MCP 서버 (OpenCode/Cline 이 자식 프로세스로 실행)
```

> 주의: `generate_requirements`/`propose_rag_contracts` 는 실제 OpenAI 과금이 발생하고
> 수 분이 걸릴 수 있다. `propose_rag_contracts` 는 파일 쓰기 도구이므로
> autoApprove(OpenCode 의 permission allow) 목록에 넣지 말 것.

### 기록 유지(상태 연속성) — Step-by-Step

`propose_rag_contracts` 는 상태를 유지한다. 실행 결과(최종 계약 + 진화 로그)를
`docs/rag_state.json` 에 저장하고, 다음 호출에서 이를 이어서 재사용한다.

#### 1단계: 첫 실행 — baseline 계약 생성

```powershell
.\ragproposal.ps1 --task "RAG 시스템 구축 요청" --out docs
```

1. 페르소나 인터뷰 → `ContractSynthesizer` 가 baseline 계약 합성
2. 역할 에이전트 5종이 제안/비판 → 최종 계약 생성
3. 산출물 저장: `docs/rag_state.json`(최종 계약 + 진화 로그), `rag_proposal.generated.yaml`, `rag_proposal.summary.json`

#### 2단계: 두 번째 실행 — 점진적 진화

```powershell
.\ragproposal.ps1 --task "위 계약을 개선해 줘" --out docs
```

1. `docs/rag_state.json` 의 **이전 최종 계약**을 `existing_contracts` 로 로드
2. 에이전트가 이전 계약 위에서 다시 제안/비판 → 계약이 점진적으로 진화
3. 진화 로그가 **이어서 누적**(iteration 번호 연속)
4. 갱신된 상태가 다시 `docs/rag_state.json` 에 저장

#### 3단계: 처음부터 다시 시작 (초기화)

```powershell
# CLI
.\ragproposal.ps1 --task "..." --out docs --fresh

# MCP: propose_rag_contracts 호출 시 fresh=true
```

→ `docs/rag_state.json` 을 무시하고 새 baseline 부터 시작한다.

#### 상태 기록 형식: JSON spec + 산출물 누적 버전

`docs/rag_state.json` 은 **JSON spec**(`spec_version`)으로, run 히스토리(`runs`)를 누적한다.
각 run 은 **에이전트 협력**(agent/role/proposals/critiques), **진화도**(iteration 별
`evolution_degree`, run 별 `evolution_degree_total`), 그리고 **산출물 버전 경로**
(`docs/versions/run_NNN/` 의 md/yaml/json)를 기록한다.

```json
{
  "spec_version": "1.0",
  "runs": [
    {
      "run_id": 1,
      "contracts": [...],
      "evolution_log": [
        { "iteration": 1, "agent": "...", "role": "...", "proposals": [...], "critiques": [...], "evolution_degree": 2 }
      ],
      "evolution_degree_total": 6,
      "artifacts": { "yaml": "versions/run_001/...", "summary": "...", "requirements": "...", "contracts_graph": "..." }
    }
  ],
  "latest_run_id": 1
}
```

#### 상태 파일 예시 (`docs/rag_state.json`)

```json
{
  "contracts": [
    { "name": "HybridRetriever", "role": "Retriever", "inputs": ["query"], "outputs": ["docs"] }
  ],
  "evolution_log": [
    {
      "iteration": 1,
      "agent": "Retriever",
      "changes": [
        { "action": "add", "name": "RankingQualityEvaluator", "detail": "새 계약 추가" }
      ]
    }
  ]
}
```
