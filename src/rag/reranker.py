"""reranker.py -- MMR 기반 다양성 재랭킹 + 근접 중복 제거.

HybridRetrievalEnhancer / LatencyAndDiversityOptimizer 계약의 구현체.
이미 계산된 검색 결과(텍스트 목록)에 대해 임베딩 재호출 없이 동작한다.
"""

from typing import List


def _jaccard(a: str, b: str) -> float:
    """공백 단위 Jaccard 유사도(0.0~1.0)."""
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def mmr_rerank(hits: List[str], top_k: int, lambda_: float = 0.7) -> List[str]:
    """MMR(Maximal Marginal Relevance) 재랭킹.

    원순위를 관련성(relevance)의 대용으로 삼고, 이미 선택된 항목과의 유사도를
    최소화하도록 재정렬한다. lambda_ 가 클수록 관련성을, 작을수록 다양성을 우선한다.
    """
    if not hits:
        return []
    n = len(hits)
    selected_idx = [0]
    remaining_idx = list(range(1, n))

    while remaining_idx and len(selected_idx) < top_k:
        def _score(i: int) -> float:
            relevance = 1.0 / (i + 1)
            max_sim = max(
                (_jaccard(hits[i], hits[j]) for j in selected_idx), default=0.0
            )
            return lambda_ * relevance - (1.0 - lambda_) * max_sim

        best = max(remaining_idx, key=_score)
        selected_idx.append(best)
        remaining_idx.remove(best)

    return [hits[i] for i in selected_idx]


def deduplicate(hits: List[str], threshold: float = 0.8) -> List[str]:
    """근접 중복 문서를 제거한다(Jaccard 유사도가 threshold 이상이면 제외)."""
    kept: List[str] = []
    for text in hits:
        if all(_jaccard(text, existing) < threshold for existing in kept):
            kept.append(text)
    return kept
