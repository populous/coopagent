"""test 공통 설정.

example/ 패키지(학습용 예시)를 임포트 경로에 추가한다.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # 프로젝트 루트
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
