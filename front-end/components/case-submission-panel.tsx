"use client";

import { startTransition, useState } from "react";
import { useRouter } from "next/navigation";

import { createMaintenanceCase } from "@/lib/api";
import { SectionCard } from "@/components/section-card";
import type { MaintenanceTaskResponse } from "@/lib/types";

type CaseSubmissionPanelProps = {
  initialTask?: MaintenanceTaskResponse | null;
  initialExportSummary?: string | null;
};

type CaseDraft = {
  title: string;
  workOrderId: string;
  assetCode: string;
  reportSource: string;
  priority: string;
  equipmentType: string;
  equipmentModel: string;
  faultType: string;
  symptomDescription: string;
  processingSteps: string;
  resolutionSummary: string;
  attachmentName: string;
  attachmentUrl: string;
};

function buildDefaultProcessingSteps(task?: MaintenanceTaskResponse | null): string {
  if (!task) {
    return "";
  }

  return task.steps
    .map((step) => {
      const statusText =
        step.status === "completed"
          ? "已完成"
          : step.status === "in_progress"
            ? "执行中"
            : step.status === "skipped"
              ? "已跳过"
              : "待执行";
      const noteText = step.completion_note ? `；备注：${step.completion_note}` : "";
      const toolText = step.required_tools.length ? `；工具：${step.required_tools.join(" / ")}` : "";
      const materialText = step.required_materials.length ? `；材料：${step.required_materials.join(" / ")}` : "";
      const durationText = step.estimated_minutes ? `；预计耗时：${step.estimated_minutes} 分钟` : "";
      return `${step.step_order}. ${step.title}（${statusText}）${noteText || `；操作：${step.instruction}`}${toolText}${materialText}${durationText}`;
    })
    .join("\n");
}

function buildInitialDraft(
  task?: MaintenanceTaskResponse | null,
  exportSummary?: string | null,
): CaseDraft {
  return {
    title: task ? `${task.title}案例` : "",
    workOrderId: task?.work_order_id || "",
    assetCode: task?.asset_code || "",
    reportSource: task?.report_source || "",
    priority: task?.priority || "medium",
    equipmentType: task?.equipment_type || "摩托车发动机",
    equipmentModel: task?.equipment_model || "",
    faultType: task?.fault_type || "",
    symptomDescription: task?.symptom_description || "",
    processingSteps: buildDefaultProcessingSteps(task),
    resolutionSummary: exportSummary || task?.advice_card || "",
    attachmentName: "",
    attachmentUrl: "",
  };
}

export function CaseSubmissionPanel({
  initialTask,
  initialExportSummary,
}: CaseSubmissionPanelProps) {
  const router = useRouter();
  const [draft, setDraft] = useState<CaseDraft>(buildInitialDraft(initialTask, initialExportSummary));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const payload = await createMaintenanceCase({
        title: draft.title,
        work_order_id: draft.workOrderId || null,
        asset_code: draft.assetCode || null,
        report_source: draft.reportSource || null,
        priority: draft.priority || null,
        equipment_type: draft.equipmentType,
        equipment_model: draft.equipmentModel || null,
        fault_type: draft.faultType || null,
        task_id: initialTask?.id || null,
        symptom_description: draft.symptomDescription,
        processing_steps: draft.processingSteps,
        resolution_summary: draft.resolutionSummary || null,
        attachment_name: draft.attachmentName || null,
        attachment_url: draft.attachmentUrl || null,
        knowledge_refs: initialTask?.source_refs || [],
      });

      startTransition(() => {
        router.push(`/cases/${payload.id}`);
      });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "案例创建失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="panelStack">
      {initialTask ? (
        <SectionCard
          title="任务上下文"
          description="当前案例将从任务执行结果预填，包含任务故障现象、步骤执行记录和知识引用。"
        >
          <div className="summaryGrid">
            <article className="resultCard">
              <h3>{initialTask.title}</h3>
              <ul className="simpleList">
                <li>任务 ID：{initialTask.id}</li>
                <li>工单编号：{initialTask.work_order_id || "未填写"}</li>
                <li>设备编号：{initialTask.asset_code || "未填写"}</li>
                <li>报修来源：{initialTask.report_source || "未填写"}</li>
                <li>工单优先级：{initialTask.priority || "medium"}</li>
                <li>设备类型：{initialTask.equipment_type}</li>
                <li>设备型号：{initialTask.equipment_model || "未填写"}</li>
                <li>故障类型：{initialTask.fault_type || "未填写"}</li>
                <li>
                  步骤进度：{initialTask.completed_steps}/{initialTask.total_steps}
                </li>
              </ul>
            </article>

            <article className="resultCard">
              <h3>引用知识</h3>
              <ul className="simpleList">
                {(initialTask.source_refs || []).map((ref) => (
                  <li key={ref.chunk_id}>
                    {ref.title} · {ref.section_reference || "章节待补充"} · {ref.page_reference || "页码待补充"}
                  </li>
                ))}
              </ul>
            </article>
          </div>
        </SectionCard>
      ) : null}

      <SectionCard
        title="案例沉淀表单"
        description="提交后会生成待审核案例，后续可补人工修正并执行审核入库。"
      >
        <div className="formGrid intakeGrid">
          <label>
            <span>案例标题</span>
            <input
              value={draft.title}
              onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))}
            />
          </label>
          <label>
            <span>工单编号</span>
            <input
              value={draft.workOrderId}
              onChange={(event) => setDraft((current) => ({ ...current, workOrderId: event.target.value }))}
            />
          </label>
          <label>
            <span>设备编号</span>
            <input
              value={draft.assetCode}
              onChange={(event) => setDraft((current) => ({ ...current, assetCode: event.target.value }))}
            />
          </label>
          <label>
            <span>报修来源</span>
            <input
              value={draft.reportSource}
              onChange={(event) => setDraft((current) => ({ ...current, reportSource: event.target.value }))}
            />
          </label>
          <label>
            <span>工单优先级</span>
            <select
              value={draft.priority}
              onChange={(event) => setDraft((current) => ({ ...current, priority: event.target.value }))}
            >
              <option value="low">低</option>
              <option value="medium">中</option>
              <option value="high">高</option>
              <option value="urgent">紧急</option>
            </select>
          </label>
          <label>
            <span>设备类型</span>
            <input
              value={draft.equipmentType}
              onChange={(event) =>
                setDraft((current) => ({ ...current, equipmentType: event.target.value }))
              }
            />
          </label>
          <label>
            <span>设备型号</span>
            <input
              value={draft.equipmentModel}
              onChange={(event) =>
                setDraft((current) => ({ ...current, equipmentModel: event.target.value }))
              }
            />
          </label>
          <label>
            <span>故障类型</span>
            <input
              value={draft.faultType}
              onChange={(event) => setDraft((current) => ({ ...current, faultType: event.target.value }))}
            />
          </label>
          <label className="fullSpan">
            <span>故障现象</span>
            <textarea
              rows={4}
              value={draft.symptomDescription}
              onChange={(event) =>
                setDraft((current) => ({ ...current, symptomDescription: event.target.value }))
              }
            />
          </label>
          <label className="fullSpan">
            <span>处理步骤</span>
            <textarea
              rows={8}
              value={draft.processingSteps}
              onChange={(event) =>
                setDraft((current) => ({ ...current, processingSteps: event.target.value }))
              }
            />
          </label>
          <label className="fullSpan">
            <span>处理结果总结</span>
            <textarea
              rows={4}
              value={draft.resolutionSummary}
              onChange={(event) =>
                setDraft((current) => ({ ...current, resolutionSummary: event.target.value }))
              }
            />
          </label>
          <label>
            <span>附件名称</span>
            <input
              value={draft.attachmentName}
              onChange={(event) =>
                setDraft((current) => ({ ...current, attachmentName: event.target.value }))
              }
            />
          </label>
          <label>
            <span>附件地址</span>
            <input
              value={draft.attachmentUrl}
              onChange={(event) =>
                setDraft((current) => ({ ...current, attachmentUrl: event.target.value }))
              }
            />
          </label>
        </div>

        <div className="buttonRow">
          <button type="button" onClick={handleSubmit} disabled={submitting}>
            {submitting ? "提交中..." : "创建待审核案例"}
          </button>
        </div>
        {error ? <p className="errorText">{error}</p> : null}
      </SectionCard>
    </div>
  );
}
