"use client";

import Link from "next/link";
import { useState } from "react";

import { addMaintenanceCaseCorrection, reviewMaintenanceCase } from "@/lib/api";
import { SectionCard } from "@/components/section-card";
import type { MaintenanceCaseResponse } from "@/lib/types";

type CaseReviewPanelProps = {
  initialCase: MaintenanceCaseResponse;
};

type CorrectionDraft = {
  correctionTarget: string;
  originalContent: string;
  correctedContent: string;
  note: string;
};

type ReviewDraft = {
  reviewerName: string;
  reviewNote: string;
};

const CASE_STATUS_LABELS: Record<string, string> = {
  pending_review: "待审核",
  approved: "已通过",
  rejected: "已驳回",
};

const CASE_STATUS_TONES: Record<string, string> = {
  pending_review: "status-review",
  approved: "status-ready",
  rejected: "status-muted",
};

const CORRECTION_LABELS: Record<string, string> = {
  retrieval_result: "检索结果",
  model_output: "模型输出",
  summary: "处理总结",
  procedure: "处理步骤",
};

function formatDate(value?: string | null): string {
  if (!value) {
    return "未记录";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString("zh-CN", {
    hour12: false,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function CaseReviewPanel({ initialCase }: CaseReviewPanelProps) {
  const [caseDetail, setCaseDetail] = useState(initialCase);
  const [correctionDraft, setCorrectionDraft] = useState<CorrectionDraft>({
    correctionTarget: "summary",
    originalContent: "",
    correctedContent: "",
    note: "",
  });
  const [reviewDraft, setReviewDraft] = useState<ReviewDraft>({
    reviewerName: caseDetail.reviewer_name || "评审老师",
    reviewNote: caseDetail.review_note || "",
  });
  const [submittingCorrection, setSubmittingCorrection] = useState(false);
  const [submittingReview, setSubmittingReview] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleCorrectionSubmit() {
    setSubmittingCorrection(true);
    setError(null);
    try {
      const payload = await addMaintenanceCaseCorrection(caseDetail.id, {
        correction_target: correctionDraft.correctionTarget,
        original_content: correctionDraft.originalContent || null,
        corrected_content: correctionDraft.correctedContent,
        note: correctionDraft.note || null,
      });
      setCaseDetail(payload);
      setCorrectionDraft({
        correctionTarget: correctionDraft.correctionTarget,
        originalContent: "",
        correctedContent: "",
        note: "",
      });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "人工修正提交失败");
    } finally {
      setSubmittingCorrection(false);
    }
  }

  async function handleReview(action: "approve" | "reject") {
    setSubmittingReview(action);
    setError(null);
    try {
      const payload = await reviewMaintenanceCase(caseDetail.id, {
        action,
        reviewer_name: reviewDraft.reviewerName || null,
        review_note: reviewDraft.reviewNote || null,
      });
      setCaseDetail(payload);
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : "案例审核失败");
    } finally {
      setSubmittingReview(null);
    }
  }

  return (
    <div className="panelStack">
      <SectionCard
        title="案例总览"
        description="这里承接任务沉淀结果，可查看引用、补修正并执行审核入库。"
      >
        <div className="panelStack">
          <div className="selectionSummary">
            <div className="resultMeta">
              <h3>{caseDetail.title}</h3>
              <p>
                {caseDetail.equipment_model || caseDetail.equipment_type} · {caseDetail.fault_type || "故障类型待补充"}
              </p>
            </div>
            <span className={`statusBadge ${CASE_STATUS_TONES[caseDetail.status] || "status-pending"}`}>
              {CASE_STATUS_LABELS[caseDetail.status] || caseDetail.status}
            </span>
          </div>

          <div className="summaryGrid">
            <article className="resultCard">
              <h3>基础信息</h3>
              <ul className="simpleList">
                <li>案例 ID：{caseDetail.id}</li>
                <li>关联任务：{caseDetail.task_id ? `#${caseDetail.task_id}` : "无"}</li>
                <li>设备类型：{caseDetail.equipment_type}</li>
                <li>设备型号：{caseDetail.equipment_model || "未填写"}</li>
                <li>知识文档：{caseDetail.source_document_id ? `#${caseDetail.source_document_id}` : "未入库"}</li>
              </ul>
              {caseDetail.task_id ? (
                <Link href={`/tasks/${caseDetail.task_id}`} className="inlineActionLink">
                  返回关联任务
                </Link>
              ) : null}
            </article>

            <article className="resultCard">
              <h3>审核状态</h3>
              <ul className="simpleList">
                <li>审核人：{caseDetail.reviewer_name || "待审核"}</li>
                <li>审核时间：{formatDate(caseDetail.reviewed_at)}</li>
                <li>审核意见：{caseDetail.review_note || "待补充"}</li>
                <li>更新时间：{formatDate(caseDetail.updated_at)}</li>
              </ul>
            </article>
          </div>

          <article className="resultCard">
            <h3>故障现象与处理结果</h3>
            <p>{caseDetail.symptom_description}</p>
            {caseDetail.resolution_summary ? <p className="muted">{caseDetail.resolution_summary}</p> : null}
          </article>
        </div>
      </SectionCard>

      <div className="twoGrid">
        <SectionCard
          title="处理步骤与知识引用"
          description="对照处理步骤、知识来源和章节页码，判断案例描述是否完整。"
        >
          <div className="stackList">
            <article className="resultCard">
              <h3>处理步骤</h3>
              <ul className="simpleList">
                {caseDetail.processing_steps.length ? (
                  caseDetail.processing_steps.map((item) => <li key={item}>{item}</li>)
                ) : (
                  <li>当前暂无处理步骤记录。</li>
                )}
              </ul>
            </article>

            <article className="resultCard">
              <h3>知识引用</h3>
              <ul className="simpleList">
                {caseDetail.knowledge_refs.length ? (
                  caseDetail.knowledge_refs.map((ref) => (
                    <li key={ref.chunk_id}>
                      {ref.title} · {ref.section_reference || "章节待补充"} · {ref.page_reference || "页码待补充"}
                    </li>
                  ))
                ) : (
                  <li>当前未绑定知识引用。</li>
                )}
              </ul>
            </article>
          </div>
        </SectionCard>

        <SectionCard
          title="人工修正与审核"
          description="先补充修正，再执行通过/驳回，审核通过后案例会沉淀为知识文档。"
        >
          <div className="panelStack">
            <article className="resultCard">
              <h3>新增人工修正</h3>
              <div className="formGrid">
                <label>
                  <span>修正目标</span>
                  <select
                    value={correctionDraft.correctionTarget}
                    onChange={(event) =>
                      setCorrectionDraft((current) => ({
                        ...current,
                        correctionTarget: event.target.value,
                      }))
                    }
                  >
                    {Object.entries(CORRECTION_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>原始内容</span>
                  <textarea
                    rows={3}
                    value={correctionDraft.originalContent}
                    onChange={(event) =>
                      setCorrectionDraft((current) => ({
                        ...current,
                        originalContent: event.target.value,
                      }))
                    }
                  />
                </label>
                <label>
                  <span>修正后内容</span>
                  <textarea
                    rows={3}
                    value={correctionDraft.correctedContent}
                    onChange={(event) =>
                      setCorrectionDraft((current) => ({
                        ...current,
                        correctedContent: event.target.value,
                      }))
                    }
                  />
                </label>
                <label>
                  <span>修正说明</span>
                  <textarea
                    rows={2}
                    value={correctionDraft.note}
                    onChange={(event) =>
                      setCorrectionDraft((current) => ({
                        ...current,
                        note: event.target.value,
                      }))
                    }
                  />
                </label>
              </div>
              <div className="buttonRow">
                <button type="button" onClick={handleCorrectionSubmit} disabled={submittingCorrection}>
                  {submittingCorrection ? "提交中..." : "提交人工修正"}
                </button>
              </div>
            </article>

            <article className="resultCard">
              <h3>审核操作</h3>
              <div className="formGrid">
                <label>
                  <span>审核人</span>
                  <input
                    value={reviewDraft.reviewerName}
                    onChange={(event) =>
                      setReviewDraft((current) => ({
                        ...current,
                        reviewerName: event.target.value,
                      }))
                    }
                  />
                </label>
                <label>
                  <span>审核意见</span>
                  <textarea
                    rows={3}
                    value={reviewDraft.reviewNote}
                    onChange={(event) =>
                      setReviewDraft((current) => ({
                        ...current,
                        reviewNote: event.target.value,
                      }))
                    }
                  />
                </label>
              </div>
              <div className="buttonRow">
                <button
                  type="button"
                  onClick={() => handleReview("approve")}
                  disabled={submittingReview !== null}
                >
                  {submittingReview === "approve" ? "提交中..." : "审核通过"}
                </button>
                <button
                  type="button"
                  className="secondaryButton"
                  onClick={() => handleReview("reject")}
                  disabled={submittingReview !== null}
                >
                  {submittingReview === "reject" ? "提交中..." : "驳回案例"}
                </button>
              </div>
            </article>

            <article className="resultCard">
              <h3>修正记录</h3>
              <ul className="simpleList">
                {caseDetail.corrections.length ? (
                  caseDetail.corrections.map((item) => (
                    <li key={item.id}>
                      {CORRECTION_LABELS[item.correction_target] || item.correction_target}：
                      {item.corrected_content}
                    </li>
                  ))
                ) : (
                  <li>当前暂无人工修正。</li>
                )}
              </ul>
            </article>
          </div>
        </SectionCard>
      </div>

      {error ? <p className="errorText">{error}</p> : null}
    </div>
  );
}
