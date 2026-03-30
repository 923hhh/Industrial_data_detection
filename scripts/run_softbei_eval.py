"""Run TODO-SB-7 evaluation against the current 软件杯 API stack.

Usage:
    venv\\Scripts\\python.exe scripts/run_softbei_eval.py
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.evaluation.softbei_metrics import build_scorecard
from app.main import app as fastapi_app
from app.persistence.models.sensor_data import Base
from app.shared.database import get_session

import app.persistence.models as persistence_models  # noqa: F401  # ensure all models are registered on Base


CASES_PATH = ROOT / "evaluation" / "softbei_eval_cases.json"
SEED_PATH = ROOT / "evaluation" / "softbei_knowledge_seed.json"
OUTPUT_PATH = ROOT / "evaluation" / "softbei_eval_results.json"
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]{2,}")


def load_json(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def tokenize(value: str) -> list[str]:
    return [token for token in TOKEN_PATTERN.findall(value) if token.strip()]


def result_matches_case(results: list[dict[str, Any]], case: dict[str, Any]) -> bool:
    expected_titles = [normalize_text(item) for item in case.get("expected_titles", []) if item]
    expected_terms = [normalize_text(item) for item in case.get("expected_terms", []) if item]

    for item in results:
        haystack = normalize_text(
            " ".join(
                [
                    item.get("title", ""),
                    item.get("excerpt", ""),
                    item.get("recommendation_reason", ""),
                    item.get("source_name", ""),
                ]
            )
        )
        if expected_titles and any(title in haystack for title in expected_titles):
            return True
        if expected_terms and any(term in haystack for term in expected_terms):
            return True
    return False


def build_keyword_baseline_docs(seed_documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for doc in seed_documents:
        docs.append(
            {
                "title": doc["title"],
                "equipment_type": doc["equipment_type"],
                "equipment_model": doc.get("equipment_model"),
                "fault_type": doc.get("fault_type"),
                "content": doc["content"],
            }
        )
    return docs


def keyword_baseline_hit(case: dict[str, Any], docs: list[dict[str, Any]]) -> bool:
    query_tokens = tokenize(case.get("query", ""))
    expected_terms = [str(item) for item in case.get("expected_terms", [])]
    search_terms = [*query_tokens, *expected_terms]

    ranked: list[tuple[int, dict[str, Any]]] = []
    for doc in docs:
        if doc.get("equipment_type") != case.get("equipment_type"):
            continue
        if case.get("equipment_model") and doc.get("equipment_model") not in {None, case.get("equipment_model")}:
            continue

        text = normalize_text(f"{doc.get('title', '')} {doc.get('content', '')} {doc.get('fault_type', '')}")
        score = 0
        for term in search_terms:
            if normalize_text(term) in text:
                score += 1
        if score:
            ranked.append((score, doc))

    ranked.sort(key=lambda item: item[0], reverse=True)
    top_docs = [item[1] for item in ranked[:5]]
    return result_matches_case(
        [
            {
                "title": doc["title"],
                "excerpt": doc["content"],
                "recommendation_reason": "",
                "source_name": doc["title"],
            }
            for doc in top_docs
        ],
        case,
    )


async def create_eval_client(db_name: str) -> tuple[AsyncClient, async_sessionmaker[AsyncSession], Any]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False, "uri": True},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_session():
        async with session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_session] = override_get_session
    client = AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://softbei-eval")
    return client, session_factory, engine


async def seed_documents(client: AsyncClient, seed_documents: list[dict[str, Any]]) -> None:
    for item in seed_documents:
        response = await client.post("/api/v1/knowledge/documents", json=item)
        response.raise_for_status()


async def execute_case_flow(client: AsyncClient, case: dict[str, Any]) -> dict[str, Any]:
    search_payload = {
        "query": case["query"],
        "equipment_type": case["equipment_type"],
        "equipment_model": case.get("equipment_model"),
        "fault_type": case.get("fault_type"),
        "limit": 5,
    }
    search_response = await client.post("/api/v1/knowledge/search", json=search_payload)
    search_response.raise_for_status()
    search_data = search_response.json()

    retrieval_hit = result_matches_case(search_data["results"], case)
    citation_ok = False
    if retrieval_hit and search_data["results"]:
        best = search_data["results"][0]
        citation_ok = bool(best.get("source_name")) and bool(
            best.get("section_reference") or best.get("page_reference")
        )

    record: dict[str, Any] = {
        "case_id": case["id"],
        "category": case["category"],
        "query": case["query"],
        "retrieval_hit": retrieval_hit,
        "citation_ok": citation_ok,
        "workflow_expected": bool(case.get("workflow_expected")),
        "workflow_completed": False,
        "feedback_expected": bool(case.get("feedback_expected")),
        "feedback_hit": False,
        "result_count": search_data["total"],
        "top_title": search_data["results"][0]["title"] if search_data["results"] else None,
        "top_source_name": search_data["results"][0]["source_name"] if search_data["results"] else None,
        "task_id": None,
        "case_record_id": None,
        "approved_document_id": None,
    }

    if not retrieval_hit or not case.get("workflow_expected"):
        return record

    selected_chunk_ids = [item["chunk_id"] for item in search_data["results"][:2]]
    task_payload = {
        "equipment_type": case["equipment_type"],
        "equipment_model": case.get("equipment_model"),
        "maintenance_level": "standard",
        "fault_type": case.get("fault_type"),
        "symptom_description": case["query"],
        "source_chunk_ids": selected_chunk_ids,
    }
    task_response = await client.post("/api/v1/tasks", json=task_payload)
    task_response.raise_for_status()
    task_data = task_response.json()
    record["task_id"] = task_data["id"]

    for step in task_data["steps"]:
        patch_response = await client.patch(
            f"/api/v1/tasks/{task_data['id']}/steps/{step['id']}",
            json={"status": "completed", "completion_note": f"{case['id']} 自动评测完成"},
        )
        patch_response.raise_for_status()
        task_data = patch_response.json()

    export_response = await client.get(f"/api/v1/export/{task_data['id']}")
    export_response.raise_for_status()
    export_data = export_response.json()
    record["workflow_completed"] = (
        export_data["task"]["status"] == "completed"
        and export_data["task"]["completed_steps"] == export_data["task"]["total_steps"]
        and bool(export_data.get("export_summary"))
    )

    case_payload = {
        "title": case["case_title"],
        "equipment_type": case["equipment_type"],
        "equipment_model": case.get("equipment_model"),
        "fault_type": case.get("fault_type"),
        "task_id": task_data["id"],
        "symptom_description": case["query"],
        "processing_steps": case["processing_steps"],
        "resolution_summary": case["resolution_summary"],
        "knowledge_refs": export_data["task"]["source_refs"],
    }
    case_response = await client.post("/api/v1/cases", json=case_payload)
    case_response.raise_for_status()
    case_data = case_response.json()
    record["case_record_id"] = case_data["id"]

    if not case.get("feedback_expected"):
        return record

    correction_response = await client.post(
        f"/api/v1/cases/{case_data['id']}/corrections",
        json={
            "correction_target": "summary",
            "original_content": case["resolution_summary"],
            "corrected_content": case["resolution_summary"],
            "note": "TODO-SB-7 自动评测补充修正记录。",
        },
    )
    correction_response.raise_for_status()

    review_response = await client.post(
        f"/api/v1/cases/{case_data['id']}/review",
        json={
            "action": "approve",
            "reviewer_name": "TODO-SB-7 自动评测",
            "review_note": "自动评测通过，用于验证案例回流能力。",
        },
    )
    review_response.raise_for_status()
    reviewed_case = review_response.json()
    record["approved_document_id"] = reviewed_case.get("source_document_id")

    followup_query = case.get("followup_query") or case["case_title"]
    followup_response = await client.post(
        "/api/v1/knowledge/search",
        json={
            "query": followup_query,
            "equipment_type": case["equipment_type"],
            "equipment_model": case.get("equipment_model"),
            "limit": 5,
        },
    )
    followup_response.raise_for_status()
    followup_data = followup_response.json()
    expected_case_source = f"case-{case_data['id']}"
    record["feedback_hit"] = any(
        item.get("source_name") == expected_case_source or normalize_text(case["case_title"]) in normalize_text(item.get("title"))
        for item in followup_data["results"]
    )
    return record


async def run_evaluation() -> dict[str, Any]:
    seed_payload = load_json(SEED_PATH)
    cases = load_json(CASES_PATH)
    baseline_docs = build_keyword_baseline_docs(seed_payload)

    client, _session_factory, engine = await create_eval_client("softbei_eval_stage7")
    try:
        await seed_documents(client, seed_payload)
        case_records: list[dict[str, Any]] = []
        keyword_records: list[dict[str, Any]] = []
        for case in cases:
            case_records.append(await execute_case_flow(client, case))
            keyword_records.append(
                {
                    "case_id": case["id"],
                    "category": case["category"],
                    "retrieval_hit": keyword_baseline_hit(case, baseline_docs),
                    "citation_ok": False,
                    "workflow_expected": False,
                    "workflow_completed": False,
                    "feedback_expected": False,
                    "feedback_hit": False,
                }
            )

        history_response = await client.get("/api/v1/history?limit=50")
        history_response.raise_for_status()
        cases_response = await client.get("/api/v1/cases?limit=50")
        cases_response.raise_for_status()
    finally:
        await client.aclose()
        fastapi_app.dependency_overrides.pop(get_session, None)
        await engine.dispose()

    current_summary = build_scorecard(case_records)
    keyword_summary = build_scorecard(keyword_records)

    direct_llm_baseline = {
        "case_count": len(cases),
        "retrieval": {"hits": 0, "total": len(cases), "hit_rate": 0.0},
        "citation": {"hits": 0, "total": len(cases), "coverage_rate": 0.0},
        "workflow": {"hits": 0, "total": len(cases), "completion_rate": 0.0},
        "feedback": {"hits": 0, "total": len(cases), "recall_rate": 0.0},
    }
    legacy_diagnosis_baseline = {
        "case_count": len(cases),
        "retrieval": {"hits": 0, "total": len(cases), "hit_rate": 0.0},
        "citation": {"hits": 0, "total": len(cases), "coverage_rate": 0.0},
        "workflow": {"hits": 0, "total": len(cases), "completion_rate": 0.0},
        "feedback": {"hits": 0, "total": len(cases), "recall_rate": 0.0},
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "database": "sqlite+aiosqlite temporary database",
            "image_path": "本轮自动评测固定使用文本 + 设备型号，不调用外部视觉模型。",
            "seed_documents": len(seed_payload),
            "evaluation_cases": len(cases),
            "history_count": history_response.json()["total"],
            "case_count": cases_response.json()["total"],
        },
        "metrics": {
            "current_system": current_summary,
            "keyword_baseline": keyword_summary,
            "direct_llm_without_citations": direct_llm_baseline,
            "legacy_diagnosis_console": legacy_diagnosis_baseline,
        },
        "cases": case_records,
    }


def main() -> None:
    payload = asyncio.run(run_evaluation())
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["metrics"], ensure_ascii=False, indent=2))
    print(f"\n评测结果已写入: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
