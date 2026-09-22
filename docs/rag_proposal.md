# 신규 RAG 시스템 제안 (coopagent 생성 산출물)

이 문서는 **coopagent 파이프라인**이 실제로 생성한 RAG 계약 제안을 정리한 것이다.
산출물은 사람이 수기 작성한 것이 아니라, `src/documentation_agent/rag_proposal.py`
드라이버가 페르소나 인터뷰 → 계약 합성 → 역할 에이전트 제안/비판 → 병합/판정 →
진화 로그 → YAML 직렬화를 전부 실행해 만들어낸 결과다.

## 생성 산출물

| 파일 | 내용 |
|---|---|
| `docs/rag_proposal.requirements.md` | 페르소나 인터뷰로부터 생성된 요구사항 문서 |
| `docs/rag_proposal.generated.yaml` | 최종 인터페이스 계약 12개 (YAML 직렬화) |
| `docs/rag_proposal.summary.json` | 비판·진화 로그·충돌/불변조건 검증 결과 요약 |

## 참고 실사례: cline-rag (populous/cline-rag)

- **구조**: LangChain+LangGraph, Ollama/OpenAI 임베딩, Chroma 로컬 영속 벡터저장소,
  RecursiveCharacterTextSplitter, BM25(rank_bm25)+CJK bigram, LangGraph StateGraph로
  vector/keyword/hybrid 분기, RRF 융합, MCP stdio 서버(도구 4개).
- **문서화된 한계**(README 설계 메모 / ARCHITECTURE.md):
  1. 임베딩 모델 변경 시 수동 `--reset` 필요(강제되지 않음)
  2. "검색 먼저" 규칙이 프로토콜이 아니라 Host 규칙 파일에만 의존
  3. 랭킹 품질 자동 평가 하니스(recall@k, MRR, latency) 부재
  4. RRF 이후 재랭킹/중복제거/출처 다양성 보장 단계 부재

## coopagent가 생성한 계약 (요약)

생성된 12개 계약은 위 한계를 겨냥해 baseline 6개에서 진화했다:

| cline-rag 한계 | 대응 계약 |
|---|---|
| ① 임베딩 모델 변경 수동 reset | `EmbeddingModelManager`, `EmbeddingModelUpdater` |
| ② 검색 프로토콜이 규칙 파일에만 의존 | `SearchProtocolManager`, `SearchProtocolOrchestrator` |
| ③ 평가 하니스 부재 | `RankingQualityEvaluator`, `RankingQualityEnhancer` |
| ④ 재랭킹/다양성/중복제거 부재 | `HybridRetrievalEnhancer`, `LatencyAndDiversityOptimizer` |
| (공통) 피드백 루프 | `FeedbackLoopIntegrator`, `FeedbackLoopEnhancer` |

### 역할 에이전트 비판이 지적한 개선점

각 역할 에이전트(Retriever/Ranker/Orchestrator/Evaluator/Logger)가 수행한
`critique_contracts` 결과, 공통적으로 다음이 지적되었다:

- **계약 중복**: `EmbeddingModelManager`↔`EmbeddingModelUpdater`, `SearchProtocolManager`↔
  `SearchProtocolOrchestrator` 등 "기본 버전"과 "Enhancer/Updater"가 유사해 통합 필요.
- **실패 모드·메트릭 구체성 부족**: 실패 대응 전략과 메트릭 정의/측정 방법이 모호.
- **계약 간 상호작용 미정의**: 계약 간 의존성·데이터 흐름이 명시되지 않음.

> 이 지적들은 요약 JSON의 `critiques` 필드에 원문으로 기록되어 있다.

## 실행 코드 (`src/rag/`)

계약 중 외부 서비스 없이 결정론적으로 구현 가능한 것들을 실제 코드로 구현했다:

| 계약 | 구현 모듈 |
|---|---|
| `RankingQualityEvaluator` | `rag/evaluator.py` (recall@k, MRR, latency_ms) |
| `HybridRetrievalEnhancer`(재랭킹/다양성/중복제거) | `rag/reranker.py` (MMR 재랭킹, Jaccard 중복 제거) |
| `Logger`(출처 추적) | `rag/provenance.py` (출처 메타데이터, 출처 목록) |

## 판정 결과

- 충돌 검출: **0건**
- 불변조건 위반: **0건**
- 진화 로그: 5 iteration (Retriever가 6개 계약 추가, 이후 에이전트는 변경 없음)
