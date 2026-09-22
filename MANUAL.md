# coopagent 사용 매뉴얼

coopagent 는 LangGraph 기반의 **페르소나-인터뷰 요구사항 생성 에이전트**다. 자연어
요구를 인터페이스 계약(`InterfaceContract`)으로 구조화하고, 역할 기반 멀티 에이전트가
계약을 제안·비판·진화시켜 RAG 등 시스템의 워크플로 명세를 만들어낸다.

이 문서는 설치부터 실행·테스트·구조·트러블슈팅까지 사용자 관점에서 전부 기록한 매뉴얼이다.

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
```

### 3.2 RAG 계약 제안 생성 (`ragproposal`)

```powershell
.\ragproposal.ps1 --task "RAG 시스템 구축 요청" --out docs   # 인터뷰 → 계약 합성 → 멀티 에이전트 제안/비판 → YAML
```

### 3.3 공통 옵션

| 옵션 | 설명 |
|---|---|
| `--task TASK` | 입력 요청. **생략하면 대화형으로 입력받는다** |
| `--k N` | 생성할 페르소나 수 (기본 5) |
| `--out DIR` | `ragproposal` 전용: 결과 저장 디렉터리 (기본 `docs`) |
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
│   │   ├── rag_proposal.py      # RAG 계약 제안 드라이버
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

---

## 6. 생성 산출물 (`docs/`)

| 파일 | 내용 |
|---|---|
| `rag_proposal.requirements.md` | 페르소나 인터뷰로 생성된 요구사항 문서 |
| `rag_proposal.generated.yaml` | 최종 인터페이스 계약 (YAML) |
| `rag_proposal.summary.json` | 에이전트 비판·진화 로그·충돌/불변조건 검증 결과 |
| `rag_proposal.md` | 실사례 vs 생성 계약 비교·분석 문서 |

---

## 7. 테스트

```powershell
.\.venv\Scripts\python.exe -m pytest test -q                    # pytest (40 tests)
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

## 8. 트러블슈팅

| 증상 | 원인/해결 |
|---|---|
| `Virtual environment not found` | `.\setup.ps1` 를 먼저 실행해 `.venv` 생성 |
| LLM 호출 시 인증 오류 | `.env` 에 `OPENAI_API_KEY=sk-...` 가 있는지 확인 |
| `.env` 가 있어도 키 인식 안 됨 | `OPENAI_API_KEY=` 접두어가 빠졌는지 확인 |
| `ModuleNotFoundError: documentation_agent` | 런처를 쓰지 않았다면 `PYTHONPATH=src` 필요 |
| `--task` 없이 실행했을 때 | 대화형 프롬프트가 뜨므로 입력 (또는 `--task` 사용) |

---

## 9. 보안 참고

- `.env` 는 `.gitignore` 에 등록되어 git 에 커밋되지 않는다.
- API 키는 코드에 하드코딩하지 않고 `load_dotenv()` 로만 읽는다.
- 키가 외부에 노출된 적이 있다면 **키 회전(재발급)**을 권장한다.

---

## 10. MCP 서버로 노출 (OpenCode/Cline 연동)

coopagent 를 OpenCode/Cline 의 TUI 에서 직접 호출할 수 있도록 MCP 서버를 제공한다.
서버는 stdio 기반 JSON-RPC 로, 도구 4개를 노출한다.

| 도구 | 설명 | 유형 |
|---|---|---|
| `generate_requirements` | 페르소나 인터뷰 → 요구사항 문서 | 읽기 (LLM) |
| `propose_rag_contracts` | 계약 합성 → 멀티 에이전트 제안/비판 → YAML | **쓰기** (LLM) |
| `list_generated_proposals` | 생성된 산출물 목록 | 읽기 |
| `get_proposal_contracts` | 산출물 파일 내용 | 읽기 |

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
