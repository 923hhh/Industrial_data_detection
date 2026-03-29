"""Metrics helpers for TODO-SB-7 software cup evaluation."""
from __future__ import annotations

from typing import Any


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def build_scorecard(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build aggregate metrics from per-case evaluation records."""
    retrieval_total = len(records)
    retrieval_hits = sum(1 for item in records if item.get("retrieval_hit"))

    cited_records = [item for item in records if item.get("retrieval_hit")]
    citation_hits = sum(1 for item in cited_records if item.get("citation_ok"))

    workflow_records = [item for item in records if item.get("workflow_expected")]
    workflow_hits = sum(1 for item in workflow_records if item.get("workflow_completed"))

    feedback_records = [item for item in records if item.get("feedback_expected")]
    feedback_hits = sum(1 for item in feedback_records if item.get("feedback_hit"))

    categories: dict[str, dict[str, int]] = {}
    for item in records:
        category = str(item.get("category") or "unknown")
        bucket = categories.setdefault(category, {"total": 0, "hit": 0})
        bucket["total"] += 1
        if item.get("retrieval_hit"):
            bucket["hit"] += 1

    return {
        "case_count": retrieval_total,
        "retrieval": {
            "hits": retrieval_hits,
            "total": retrieval_total,
            "hit_rate": _safe_rate(retrieval_hits, retrieval_total),
        },
        "citation": {
            "hits": citation_hits,
            "total": len(cited_records),
            "coverage_rate": _safe_rate(citation_hits, len(cited_records)),
        },
        "workflow": {
            "hits": workflow_hits,
            "total": len(workflow_records),
            "completion_rate": _safe_rate(workflow_hits, len(workflow_records)),
        },
        "feedback": {
            "hits": feedback_hits,
            "total": len(feedback_records),
            "recall_rate": _safe_rate(feedback_hits, len(feedback_records)),
        },
        "category_breakdown": {
            name: {
                "hits": values["hit"],
                "total": values["total"],
                "hit_rate": _safe_rate(values["hit"], values["total"]),
            }
            for name, values in categories.items()
        },
    }
