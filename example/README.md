# example: rag 2회 재실행 (상태 연속성 시연)

`ragproposal` 을 **2회 연속 실행**해, 상태 연속성(이전 계약 로드 → 점진적 진화 → 진화 로그 누적)을 직접 따라 해 볼 수 있는 예시다.

## 준비

프로젝트 루트에 `.venv` 와 `.env`(`OPENAI_API_KEY`)가 준비되어 있어야 한다.

```powershell
powershell -ExecutionPolicy Bypass -File ..\setup.ps1
```

## 실행

### Windows (PowerShell)

```powershell
.\example\run_twice.ps1
```

### Linux / Codespaces (bash)

```bash
bash example/run_twice.sh
```

## 무엇이 일어나는가

| 단계 | 동작 |
|---|---|
| **1차 실행** | 페르소나 인터뷰 → baseline 계약 합성 → 에이전트 제안/비판 → 최종 계약 + `rag_state.json`(run 1) 저장 |
| **2차 실행** | 이전 최종 계약을 `existing_contracts` 로 로드 → 그 위에서 재제안/비판 → 계약 진화 + `rag_state.json`(run 2) **누적** |
| **상태 요약** | `show_state.py` 가 run 히스토리·에이전트 협력·진화도를 출력 |

## 결과 확인

```powershell
# JSON spec (run 히스토리 + 협력 + 진화도)
Get-Content example\output\rag_state.json

# 산출물 누적 버전 (md/yaml/json)
Get-ChildItem example\output\versions -Recurse

# 계약 그래프 (Mermaid)
Get-Content example\output\contracts_graph.md
```

- 산출물은 `example/output/` 에 저장된다.
- 버전별 산출물은 `example/output/versions/run_NNN/` 에 누적된다.
- 2차 실행 후 `show_state.py` 출력에서 `runs: 2` 와 iteration 이어짐(예: 1~5 → 6~10)을 확인할 수 있다.
