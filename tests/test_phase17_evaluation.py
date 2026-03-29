"""Phase 17: 软件杯效果证据与测试报告资产验证."""
import json
from pathlib import Path
import subprocess

import pytest

from app.evaluation.softbei_metrics import build_scorecard


ROOT = Path("e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project")


def test_softbei_eval_case_asset_count():
    """标准案例资产应保持在 10 到 20 个之间，并覆盖成功/模糊/失败场景。"""
    cases = json.loads((ROOT / "evaluation" / "softbei_eval_cases.json").read_text(encoding="utf-8"))

    assert 10 <= len(cases) <= 20
    categories = {item["category"] for item in cases}
    assert categories == {"success", "fuzzy", "failure"}


def test_build_scorecard_metrics():
    """评测汇总指标应正确计算比例和分类命中率。"""
    payload = build_scorecard(
        [
            {
                "case_id": "A",
                "category": "success",
                "retrieval_hit": True,
                "citation_ok": True,
                "workflow_expected": True,
                "workflow_completed": True,
                "feedback_expected": False,
                "feedback_hit": False,
            },
            {
                "case_id": "B",
                "category": "failure",
                "retrieval_hit": False,
                "citation_ok": False,
                "workflow_expected": False,
                "workflow_completed": False,
                "feedback_expected": False,
                "feedback_hit": False,
            },
            {
                "case_id": "C",
                "category": "success",
                "retrieval_hit": True,
                "citation_ok": False,
                "workflow_expected": True,
                "workflow_completed": False,
                "feedback_expected": True,
                "feedback_hit": True,
            },
        ]
    )

    assert payload["retrieval"]["hit_rate"] == 66.67
    assert payload["citation"]["coverage_rate"] == 50.0
    assert payload["workflow"]["completion_rate"] == 50.0
    assert payload["feedback"]["recall_rate"] == 100.0
    assert payload["category_breakdown"]["success"]["hit_rate"] == 100.0


def test_softbei_evaluation_script_generates_report():
    """评测脚本应在项目 venv 下成功运行并生成固定结果文件。"""
    python_exe = ROOT / "venv" / "Scripts" / "python.exe"
    result = subprocess.run(
        [str(python_exe), "scripts/run_softbei_eval.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "评测结果已写入" in result.stdout

    payload = json.loads((ROOT / "evaluation" / "softbei_eval_results.json").read_text(encoding="utf-8"))
    assert payload["metrics"]["current_system"]["retrieval"]["hits"] == 8
    assert payload["metrics"]["current_system"]["workflow"]["completion_rate"] == 100.0
    assert payload["metrics"]["current_system"]["feedback"]["recall_rate"] == 100.0
