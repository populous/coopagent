#!/usr/bin/env bash
# rag 2회 재실행 예시 - 상태 연속성(로드 -> 진화 -> 로그 누적)을 직접 체험
set -euo pipefail

EXAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$EXAMPLE_DIR")"
PYTHON="$ROOT/.venv/bin/python"
OUT_DIR="$EXAMPLE_DIR/output"

if [ ! -x "$PYTHON" ]; then
    echo "가상환경(.venv)이 없습니다. 먼저 프로젝트 루트에서 셋업을 실행하세요." >&2
    exit 1
fi

export PYTHONPATH="$ROOT/src"

echo "=== 1차 실행: baseline 계약 생성 ==="
"$PYTHON" -m documentation_agent.rag_proposal --task "Build a RAG search system with Chroma vectorstore and BM25 hybrid search, embedding model version management" --k 2 --out "$OUT_DIR"

echo ""
echo "=== 2차 실행: 점진적 진화 (이전 계약 로드) ==="
"$PYTHON" -m documentation_agent.rag_proposal --task "Add MMR diversity re-ranking and provenance tracking to the contracts" --k 2 --out "$OUT_DIR"

echo ""
echo "=== 상태 요약 ==="
"$PYTHON" "$EXAMPLE_DIR/show_state.py" "$OUT_DIR"
