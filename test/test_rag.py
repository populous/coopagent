"""test_rag.py -- 실행 코드(evaluator/reranker/provenance) 단위 테스트."""

from rag.evaluator import latency_ms, mrr, recall_at_k
from rag.provenance import attach_provenance, unique_sources
from rag.reranker import deduplicate, mmr_rerank


def test_recall_at_k_full_hit():
    assert recall_at_k(["a", "b"], ["a", "b", "c"], k=2) == 1.0


def test_recall_at_k_partial_hit():
    assert recall_at_k(["a", "b"], ["a", "c"], k=2) == 0.5


def test_recall_at_k_empty_truth():
    assert recall_at_k([], ["a"], k=1) == 0.0


def test_mrr_ranks_first():
    assert mrr(["a"], ["a", "b"]) == 1.0


def test_mrr_ranks_second():
    assert mrr(["a"], ["b", "a"]) == 0.5


def test_mrr_no_hit():
    assert mrr(["a"], ["b", "c"]) == 0.0


def test_latency_ms():
    assert latency_ms(1.5) == 1500.0


def test_mmr_rerank_keeps_top_k():
    hits = ["doc a", "doc b", "doc c", "doc d"]
    result = mmr_rerank(hits, top_k=2)
    assert len(result) == 2
    assert result[0] == "doc a"


def test_mmr_rerank_handles_empty():
    assert mmr_rerank([], top_k=3) == []


def test_deduplicate_removes_near_duplicates():
    hits = ["foo bar baz", "foo bar baz qux", "completely different"]
    result = deduplicate(hits, threshold=0.6)
    assert len(result) == 2
    assert "completely different" in result


def test_attach_provenance_adds_metadata():
    hits = [{"text": "hello"}, {"text": "world"}]
    result = attach_provenance(hits, source="doc.md")
    assert result[0]["source"] == "doc.md"
    assert result[1]["chunk_index"] == 1
    # 원본은 변경되지 않아야 한다
    assert "source" not in hits[0]


def test_unique_sources_dedups():
    hits = [
        {"source": "a.md"},
        {"source": "b.md"},
        {"source": "a.md"},
    ]
    assert unique_sources(hits) == ["a.md", "b.md"]
