# 상태 연속성(로드 → 점진적 진화 → 로그 누적) 실증 예제

`propose_rag_contracts`(또는 `ragproposal`)가 `docs/rag_state.json` 을 로드해 계약을
**점진적으로 진화**시키고, 진화 로그를 **이어서 누적**하는 것을 실제 실행으로 검증했다.

## 1차 실행 — baseline 계약 생성

```powershell
.\ragproposal.ps1 --task "RAG 검색 시스템 구축 - 임베딩 모델 버전 관리와 평가 하니스 필요" --k 2 --out docs
```

- 계약 수: **11개** (baseline 5 → final 11)
- 진화 로그: **5개 항목** (iteration 1~5)

## 2차 실행 — 점진적 진화

```powershell
.\ragproposal.ps1 --task "위 RAG 계약에 재랭킹(MMR 다양성)과 출처 추적(provenance)을 추가해 개선" --k 2 --out docs
```

- `docs/rag_state.json` 의 이전 11개 계약을 `existing_contracts` 로 로드
- 계약 수: **14개** (11 → 14)
- 진화 로그: **10개 항목** (iteration 1~5 유지 + 6~10 누적)

## 진화 로그 누적 확인

| iteration | agent | changes | 구분 |
|---|---|---|---|
| 1 | Retriever | 2건 | 1차 실행 |
| 2 | Ranker | 2건 | 1차 실행 |
| 3 | Orchestrator | 1건 | 1차 실행 |
| 4 | Evaluator | 1건 | 1차 실행 |
| 5 | Logger | 0건 | 1차 실행 |
| **6** | **Retriever** | **2건** | **2차 실행(누적)** |
| **7** | **Ranker** | **0건** | **2차 실행(누적)** |
| **8** | **Orchestrator** | **1건** | **2차 실행(누적)** |
| **9** | **Evaluator** | **0건** | **2차 실행(누적)** |
| **10** | **Logger** | **0건** | **2차 실행(누적)** |

> 핵심: 2차 실행에서 iteration 6~10 이 **이어서 추가**되어 진화 로그가 5 → 10 으로
> 누적된다. 즉 `existing_contracts`(이전 11개) 위에서 에이전트가 다시 제안/비판했다.

## 계약 그래프 반영

계약 집합은 `docs/contracts_graph.md` 에 Mermaid 그래프로도 저장된다. 노드는 계약
(name+role, 역할별 색상), 엣지는 데이터 흐름(outputs ↔ inputs 토큰 겹침)이다.

상태 연속성으로 인해 그래프에도 계약 진화가 반영된다:

| 구분 | 그래프 노드 수 | 변화 |
|---|---|---|
| 1차 실행 | 11개 | — |
| 2차 실행 | **14개** | 신규 3개 추가 |

2차 실행에서 그래프에 추가된 노드:

- `MMR Diversity Re-ranking` (Ranker)
- `Provenance Tracking` (Orchestrator)
- `Provenance and Diversity Enhanced Retrieval` (Orchestrator)

```powershell
# 계약 그래프 확인
Get-Content docs\contracts_graph.md
```

## 직접 확인

```powershell
python -c "import json; d=json.load(open('docs/rag_state.json', encoding='utf-8')); print('계약:', len(d['contracts']), '/ 로그:', len(d['evolution_log']))"
```

## 처음부터 다시 시작하려면

```powershell
.\ragproposal.ps1 --task "..." --out docs --fresh   # 상태 무시, 새 baseline 부터
```
