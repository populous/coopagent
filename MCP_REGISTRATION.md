# coopagent MCP 서버 등록 가이드 (Cline / OpenCode)

coopagent 의 MCP 서버(`src/documentation_agent/mcp_server.py`)를 **Cline** 과 **OpenCode**
에 등록하는 방법을 각각 정리한다. 등록하면 각 클라이언트의 TUI 채팅에서 아래 도구 4개를
호출할 수 있다.

| 도구 | 설명 | 유형 |
|---|---|---|
| `generate_requirements` | 페르소나 인터뷰 → 요구사항 문서(+그래프) | 읽기 (LLM) |
| `propose_rag_contracts` | 계약 합성 → 멀티 에이전트 제안/비판 → YAML | **쓰기** (LLM) |
| `list_generated_proposals` | 생성된 산출물 목록 | 읽기 |
| `get_proposal_contracts` | 산출물 파일 내용 | 읽기 |

> 등록용 JSON 조각은 `--mcp-print` 로 언제든 다시 확인할 수 있다.

---

## 1. Cline 에 등록

### 설정 파일
`~/.cline/data/settings/cline_mcp_settings.json`

### 방법 A: 자동 등록 (권장)

```powershell
.\documentagent.ps1 --mcp-install            # 기본 target = cline
.\documentagent.ps1 --mcp-install --force    # 기존 등록 덮어쓰기
```

### 방법 B: 수동 등록

1. `.\documentagent.ps1 --mcp-print` 로 JSON 조각 출력
2. 위 설정 파일의 `mcpServers` 에 병합:

```json
{
  "mcpServers": {
    "coopagent": {
      "command": "<절대경로>\\.venv\\Scripts\\python.exe",
      "args": [
        "<절대경로>\\src\\documentation_agent\\mcp_server.py"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": [
        "list_generated_proposals",
        "get_proposal_contracts"
      ]
    }
  }
}
```

3. Cline 재시작

### 확인

```powershell
.\documentagent.ps1 --mcp-status
```

---

## 2. OpenCode 에 등록

### 설정 파일
`~/.config/opencode/opencode.json`

### 방법 A: 자동 등록

```powershell
.\documentagent.ps1 --mcp-install --mcp-target opencode
.\documentagent.ps1 --mcp-install --mcp-target opencode --force
```

### 방법 B: 수동 등록

1. `.\documentagent.ps1 --mcp-print --mcp-target opencode` 로 JSON 조각 출력
2. 설정 파일의 `mcp` 에 병합:

```json
{
  "mcp": {
    "coopagent": {
      "type": "local",
      "command": [
        "<절대경로>\\.venv\\Scripts\\python.exe",
        "<절대경로>\\src\\documentation_agent\\mcp_server.py"
      ],
      "enabled": true
    }
  }
}
```

3. OpenCode 재시작

### 확인

```powershell
.\documentagent.ps1 --mcp-status --mcp-target opencode
```

---

## 3. Cline vs OpenCode 스키마 차이

| 항목 | Cline | OpenCode |
|---|---|---|
| 설정 파일 | `~/.cline/data/settings/cline_mcp_settings.json` | `~/.config/opencode/opencode.json` |
| 최상위 키 | `mcpServers` | `mcp` |
| 실행 지정 | `command` + `args`(배열) 분리 | `command`(실행파일+인자 한 배열) + `type: "local"` |
| 비활성화 플래그 | `disabled: true` | `enabled: false` |
| 자동 승인 | `autoApprove`(도구명 배열) | 별도 `permission` 설정 |

---

## 4. 자동 승인(autoApprove/permission) 주의

- **읽기 전용 도구만** 자동 승인 허용: `list_generated_proposals`, `get_proposal_contracts`
- `generate_requirements`/`propose_rag_contracts` 는 **실제 OpenAI 과금**이 발생하고
  수 분이 걸릴 수 있으므로 자동 승인 목록에 넣지 말 것.
- 특히 `propose_rag_contracts` 는 `docs/` 에 파일을 쓰는 **쓰기 도구**라 매번 사용자
  승인을 받아야 안전하다.
- Cline 은 `autoApprove` 배열(위 JSON)에, OpenCode 는 자체 `permission` 설정에서
  도구별 허용 여부를 별도로 관리한다.

---

## 5. 서버 직접 실행 (등록 없이 스모크 테스트)

```powershell
.\coopagent-mcp.ps1    # stdio MCP 서버 (OpenCode/Cline 이 자식 프로세스로 실행)
```
