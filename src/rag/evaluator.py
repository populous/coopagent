"""evaluator.py -- RAG 검색 품질 평가(recall@k, MRR, latency).

RankingQualityEvaluator 계약의 구현체. 순수 파이썬으로 결정론적으로 계산한다.
"""

from typing import List


def recall_at_k(ground_truth: List[str], retrieved: List[str], k: int) -> float:
    """ground_truth 중 retrieved[:k] 에 포함된 문서의 비율을 돌려준다."""
    if not ground_truth:
        return 0.0
    top = retrieved[:k]
    hits = sum(1 for doc in ground_truth if doc in top)
    return hits / len(ground_truth)


def mrr(ground_truth: List[str], retrieved: List[str]) -> float:
    """첫 정답 문서의 역순위를 돌려준다(단일 쿼리 기준, 없으면 0.0)."""
    for rank, doc in enumerate(retrieved, start=1):
        if doc in ground_truth:
            return 1.0 / rank
    return 0.0


def latency_ms(seconds: float) -> float:
    """초 단위 지연시간을 밀리초로 환산한다."""
    return seconds * 1000.0
