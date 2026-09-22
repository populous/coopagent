"""provenance.py -- 출처 추적 + 근접 중복 제거(검색 결과 메타데이터 보강).

Logger / 다양성 보장 계약의 구현체. 검색 결과(hit dict)에 출처와 청크 인덱스를
부착하고, 중복 청크를 제거한다.
"""

from typing import Dict, List


def attach_provenance(hits: List[Dict], source: str) -> List[Dict]:
    """각 hit에 출처(source)와 청크 인덱스를 부착해 돌려준다(원본은 변경하지 않음)."""
    out: List[Dict] = []
    for index, hit in enumerate(hits):
        item = dict(hit)
        item.setdefault("source", source)
        item.setdefault("chunk_index", index)
        out.append(item)
    return out


def unique_sources(hits: List[Dict]) -> List[str]:
    """hit 목록에서 중복 없이 출처 목록을 돌려준다."""
    seen: List[str] = []
    for hit in hits:
        source = str(hit.get("source", ""))
        if source and source not in seen:
            seen.append(source)
    return seen
