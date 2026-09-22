"""example/show_state.py -- rag_state.json 의 run 히스토리/협력/진화도 요약 출력.

사용 예:
    python example/show_state.py example/output
"""

import json
import sys
from pathlib import Path


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("example/output")
    path = out_dir / "rag_state.json"
    if not path.is_file():
        print(f"상태 파일 없음: {path} (먼저 ragproposal 을 실행하세요)")
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"spec_version: {data.get('spec_version', '?')}")
    runs = data.get("runs", [])
    print(f"runs: {len(runs)}")
    for run in runs:
        print(f"  run {run['run_id']}: contracts={run['contracts_count']}, "
              f"degree_total={run['evolution_degree_total']}")
        for e in run.get("evolution_log", []):
            print(f"    it {e['iteration']} {e['agent']} (role={e['role']}) "
                  f"proposals={len(e['proposals'])} critiques={len(e['critiques'])} "
                  f"degree={e['evolution_degree']}")
        arts = run.get("artifacts", {})
        print(f"    artifacts: {', '.join(arts.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
