# GitHub Codespaces에서 coopagent 실행 (Step-by-Step)

이 문서는 coopagent 를 **GitHub Codespaces** 에서 실행하고, **요구사항을 질문**한 뒤
그 결과(요구사항 문서 + 요구사항 그래프)를 보는 과정을 단계별로 정리한다.

> Codespaces 는 Linux 컨테이너다. 로컬(Windows)에서 쓰는 `.ps1`/`.cmd` 런처 대신
> `python -m` 으로 직접 실행한다. 핵심 코드(`src/`)는 크로스 플랫폼이다.
> 이 저장소의 `.devcontainer/devcontainer.json` 이 가상환경+의존성 설치를 자동으로
> 수행하므로, 아래 2번(수동 설치)은 자동 설치가 안 됐을 때만 쓰면 된다.

---

## 1. Codespaces 열기

1. https://github.com/populous/coopagent 접속
2. `Code` 버튼 → `Codespaces` 탭 → `Create codespace on main`
3. 컨테이너가 준비될 때까지 대기(수십 초~1분)

---

## 2. 가상환경 + 의존성 설치 (자동 설치가 안 됐을 때만)

Codespaces 터미널에서:

```bash
cd /workspaces/coopagent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

---

## 3. API 키 설정 (둘 중 하나)

### 방법 A: Codespaces 시크릿 (권장)

1. GitHub → 본인 아바타 → **Settings** → **Codespaces** → **Secrets** → **New secret**
2. 이름 `OPENAI_API_KEY`, 값에 API 키 입력, 저장소 `populous/coopagent` 접근 허용
3. 이미 실행 중인 Codespace 는 재시작해야 반영된다

### 방법 B: `.env` 파일

```bash
echo "OPENAI_API_KEY=sk-..." > .env
```

> `load_dotenv()` 는 이미 설정된 환경변수를 덮어쓰지 않으므로, 방법 A(시크릿)로
> 주입된 `OPENAI_API_KEY` 는 `.env` 없이도 그대로 사용된다.

---

## 4. 요구사항 질문 → 요구사항 문서 생성

```bash
export PYTHONPATH=src
python -m documentation_agent.cli --task "온라인 서점: 책 검색/장바구니/주문 기능"
```

→ 페르소나 인터뷰가 수행되고, **요구사항 문서**가 터미널에 출력된다.

---

## 5. 요구사항을 그래프로 구조화해 보기

```bash
python -m documentation_agent.cli --task "온라인 서점: 책 검색/장바구니/주문 기능" --graph
```

→ 요구사항 문서 + **요구사항 그래프(Mermaid)** 가 출력되고,
`docs/requirements_graph.md` 에 저장된다.

---

## 6. 결과 보기 (Mermaid 렌더링)

- **GitHub 에서**: `docs/requirements_graph.md` 파일을 열면 GitHub 가 Mermaid 를 자동 렌더링
- **Codespaces VS Code 에서**: `docs/requirements_graph.md` 열기 → 미리보기(`Ctrl+Shift+V`)
  - `Markdown Preview Mermaid` 확장 설치 시 다이어그램이 그대로 보인다
  - devcontainer 가 이 확장을 자동 설치한다

---

## 7. (선택) 테스트

```bash
python -m pytest test -q
```

---

## 8. (선택) MCP 서버 실행

```bash
python -m documentation_agent.mcp_server
```

---

## 참고: CMake/CTest

Codespaces(Linux) 에서는 `CMakePresets.json` 이 Windows(Visual Studio) 기준이라
`cmake --preset` 대신 `python -m pytest test -q` 를 쓰는 것을 권장한다.
