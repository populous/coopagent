# rag 2회 재실행 예시 - 상태 연속성(로드 -> 진화 -> 로그 누적)을 직접 체험
$ErrorActionPreference = "Stop"
$ExampleDir = Split-Path -Parent $MyInvocation.MyCommand.Path   # example/
$Root = Split-Path -Parent $ExampleDir                            # 프로젝트 루트
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$OutDir = Join-Path $ExampleDir "output"

if (-not (Test-Path $Python)) {
    Write-Host "가상환경(.venv)이 없습니다. 먼저 프로젝트 루트에서 setup.ps1 을 실행하세요." -ForegroundColor Red
    exit 1
}

$env:PYTHONPATH = Join-Path $Root "src"

Write-Host "=== 1차 실행: baseline 계약 생성 ===" -ForegroundColor Cyan
& $Python -m documentation_agent.rag_proposal --task "Build a RAG search system with Chroma vectorstore and BM25 hybrid search, embedding model version management" --k 2 --out $OutDir

Write-Host "`n=== 2차 실행: 점진적 진화 (이전 계약 로드) ===" -ForegroundColor Cyan
& $Python -m documentation_agent.rag_proposal --task "Add MMR diversity re-ranking and provenance tracking to the contracts" --k 2 --out $OutDir

Write-Host "`n=== 상태 요약 ===" -ForegroundColor Cyan
& $Python "$ExampleDir\show_state.py" $OutDir
