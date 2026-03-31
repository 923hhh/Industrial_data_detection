"use client";

import Link from "next/link";
import { useState } from "react";

import { getMaintenanceTaskExport, updateMaintenanceTaskStep } from "@/lib/api";
import { SectionCard } from "@/components/section-card";
import type { MaintenanceTaskResponse } from "@/lib/types";

type TaskExecutionPanelProps = {
  initialTask: MaintenanceTaskResponse;
  initialExportSummary?: string | null;
};

const TASK_STATUS_LABELS: Record<string, string> = {
  pending: "待执行",
  in_progress: "执行中",
  completed: "已完成",
  skipped: "已跳过",
};

const TASK_STATUS_TONES: Record<string, string> = {
  pending: "status-pending",
  in_progress: "status-review",
  completed: "status-ready",
  skipped: "status-muted",
};

const MAINTENANCE_LEVEL_LABELS: Record<string, string> = {
  routine: "例行检修",
  standard: "标准检修",
  emergency: "应急处置",
};

const PRIORITY_LABELS: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
  urgent: "紧急",
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

function buildDefaultNotes(task: MaintenanceTaskResponse): Record<number, string> {
  return Object.fromEntries(task.steps.map((step) => [step.id, step.completion_note || ""]));
}

export function TaskExecutionPanel({
  initialTask,
  initialExportSummary,
}: TaskExecutionPanelProps) {
  const [task, setTask] = useState(initialTask);
  const [exportSummary, setExportSummary] = useState(initialExportSummary || "");
  const [noteDrafts, setNoteDrafts] = useState<Record<number, string>>(buildDefaultNotes(initialTask));
  const [updatingStepId, setUpdatingStepId] = useState<number | null>(null);
  const [refreshingExport, setRefreshingExport] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshExportSummary() {
    setRefreshingExport(true);
    try {
      const payload = await getMaintenanceTaskExport(task.id);
      setExportSummary(payload.export_summary);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "导出摘要刷新失败");
    } finally {
      setRefreshingExport(false);
    }
  }

  async function handleStepUpdate(stepId: number, status: string) {
    setUpdatingStepId(stepId);
    setError(null);
    try {
      const payload = await updateMaintenanceTaskStep(task.id, stepId, {
        status,
        completion_note: noteDrafts[stepId] || null,
      });
      setTask(payload);
      setNoteDrafts(buildDefaultNotes(payload));

      try {
        const exported = await getMaintenanceTaskExport(payload.id);
        setExportSummary(exported.export_summary);
      } catch {
        setExportSummary("");
      }
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "步骤状态更新失败");
    } finally {
      setUpdatingStepId(null);
    }
  }

  return (
    <div className="panelStack">
      <SectionCard
        title="任务总览"
        description="这里承接 Agent 协作生成的正式任务，可直接执行步骤、补备注并刷新导出摘要。"
      >
        <div className="panelStack">
          <div className="selectionSummary">
            <div className="resultMeta">
              <h3>{task.title}</h3>
              <p>
                {task.equipment_model || task.equipment_type} ·{" "}
                {MAINTENANCE_LEVEL_LABELS[task.maintenance_level] || task.maintenance_level} ·{" "}
                {task.fault_type || "故障类型待补充"}
              </p>
            </div>
            <span className={`statusBadge ${TASK_STATUS_TONES[task.status] || "status-pending"}`}>
              {TASK_STATUS_LABELS[task.status] || task.status}
            </span>
          </div>

          <div className="summaryGrid">
            <article className="resultCard">
              <h3>任务摘要</h3>
              <ul className="simpleList">
                <li>工单编号：{task.work_order_id || "未填写"}</li>
                <li>设备编号：{task.asset_code || "未填写"}</li>
                <li>报修来源：{task.report_source || "未填写"}</li>
                <li>工单优先级：{PRIORITY_LABELS[task.priority || "medium"] || task.priority || "中"}</li>
                <li>设备类型：{task.equipment_type}</li>
                <li>设备型号：{task.equipment_model || "未填写"}</li>
                <li>故障类型：{task.fault_type || "未填写"}</li>
                <li>当前进度：{task.completed_steps}/{task.total_steps}</li>
                <li>创建时间：{formatDate(task.created_at)}</li>
                <li>更新时间：{formatDate(task.updated_at)}</li>
              </ul>
            </article>

            <article className="resultCard">
              <h3>智能建议与导出摘要</h3>
              <p>{task.advice_card || "当前暂无附加智能建议。"}</p>
              {exportSummary ? <p className="muted">{exportSummary}</p> : null}
              <div className="buttonRow">
                <button
                  type="button"
                  className="secondaryButton"
                  onClick={refreshExportSummary}
                  disabled={refreshingExport}
                >
                  {refreshingExport ? "刷新中..." : "刷新导出摘要"}
                </button>
                <Link href={`/tasks/${task.id}/export`} className="inlineActionLink">
                  导出作业单
                </Link>
                <Link href={`/cases/new?taskId=${task.id}`} className="inlineActionLink">
                  沉淀案例
                </Link>
              </div>
            </article>
          </div>

          {task.symptom_description ? (
            <article className="resultCard">
              <h3>故障现象</h3>
              <p>{task.symptom_description}</p>
            </article>
          ) : null}
        </div>
      </SectionCard>

      <div className="twoGrid">
        <SectionCard
          title="步骤执行区"
          description="按标准步骤推进任务，可随时更新状态和执行备注。"
        >
          <div className="stackList">
            {task.steps.map((step) => (
              <article key={step.id} className="stepCard">
                <div className="stepHeader">
                  <div className="resultMeta">
                    <p className="eyebrow">STEP {step.step_order}</p>
                    <h3>{step.title}</h3>
                  </div>
                  <span className={`statusBadge ${TASK_STATUS_TONES[step.status] || "status-pending"}`}>
                    {TASK_STATUS_LABELS[step.status] || step.status}
                  </span>
                </div>

                <p>{step.instruction}</p>
                {step.estimated_minutes ? <p className="muted">预计耗时：约 {step.estimated_minutes} 分钟</p> : null}
                {step.required_tools.length ? <p className="muted">工具：{step.required_tools.join(" / ")}</p> : null}
                {step.required_materials.length ? (
                  <p className="muted">材料：{step.required_materials.join(" / ")}</p>
                ) : null}
                {step.risk_warning ? <p className="errorText">风险：{step.risk_warning}</p> : null}
                {step.caution ? <p className="muted">注意：{step.caution}</p> : null}
                {step.confirmation_text ? <p className="muted">确认：{step.confirmation_text}</p> : null}

                <label className="stepNoteField">
                  <span>执行备注</span>
                  <textarea
                    value={noteDrafts[step.id] || ""}
                    rows={3}
                    onChange={(event) =>
                      setNoteDrafts((current) => ({
                        ...current,
                        [step.id]: event.target.value,
                      }))
                    }
                  />
                </label>

                <div className="stepActionGroup">
                  <button
                    type="button"
                    className="secondaryButton"
                    onClick={() => handleStepUpdate(step.id, "in_progress")}
                    disabled={updatingStepId === step.id}
                  >
                    执行中
                  </button>
                  <button
                    type="button"
                    onClick={() => handleStepUpdate(step.id, "completed")}
                    disabled={updatingStepId === step.id}
                  >
                    {updatingStepId === step.id ? "提交中..." : "标记完成"}
                  </button>
                  <button
                    type="button"
                    className="secondaryButton"
                    onClick={() => handleStepUpdate(step.id, "skipped")}
                    disabled={updatingStepId === step.id}
                  >
                    跳过
                  </button>
                </div>
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          title="知识引用依据"
          description="这里保留任务级知识引用，执行过程中可对照章节和摘录做复核。"
        >
          <div className="stackList">
            {task.source_refs.length ? (
              task.source_refs.map((ref) => (
                <article key={ref.chunk_id} className="resultCard">
                  <div className="resultMeta">
                    <h3>{ref.title}</h3>
                    <p>
                      {ref.source_name} · {ref.section_reference || "章节待补充"} ·{" "}
                      {ref.page_reference || "页码待补充"}
                    </p>
                  </div>
                  <p className="excerpt">{ref.excerpt}</p>
                </article>
              ))
            ) : (
              <p className="muted">当前任务未绑定明确知识条目，建议回到 Agent 协作页补锁定依据后再创建。</p>
            )}
          </div>
        </SectionCard>
      </div>

      {error ? <p className="errorText">{error}</p> : null}
    </div>
  );
}
