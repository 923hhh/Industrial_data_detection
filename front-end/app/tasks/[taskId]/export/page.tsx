import { notFound } from "next/navigation";

import { TaskExportActions } from "@/components/task-export-actions";
import { getMaintenanceTask, getMaintenanceTaskExport } from "@/lib/api";

type TaskExportPageProps = {
  params: Promise<{
    taskId: string;
  }>;
};

const TASK_STATUS_LABELS: Record<string, string> = {
  pending: "待执行",
  in_progress: "执行中",
  completed: "已完成",
  skipped: "已跳过",
};

const PRIORITY_LABELS: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
  urgent: "紧急",
};

const MAINTENANCE_LEVEL_LABELS: Record<string, string> = {
  routine: "例行检修",
  standard: "标准检修",
  emergency: "应急处置",
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

export default async function TaskExportPage({ params }: TaskExportPageProps) {
  const { taskId } = await params;
  const numericTaskId = Number(taskId);

  if (!Number.isFinite(numericTaskId) || numericTaskId <= 0) {
    notFound();
  }

  let task;
  try {
    task = await getMaintenanceTask(numericTaskId);
  } catch {
    notFound();
  }

  let exportSummary = "";
  let exportedAt: string | null = null;
  try {
    const exported = await getMaintenanceTaskExport(numericTaskId);
    exportSummary = exported.export_summary;
    exportedAt = exported.exported_at;
  } catch {
    exportSummary = "";
    exportedAt = null;
  }

  return (
    <div className="exportPage">
      <TaskExportActions taskId={task.id} />

      <article className="exportSheet">
        <header className="exportHeader">
          <div>
            <p className="eyebrow">Maintenance Work Order</p>
            <h1>{task.title}</h1>
            <p className="exportLead">
              正式作业单用于答辩展示、现场打印和任务归档，汇总工单上下文、结构化步骤、执行备注和知识依据。
            </p>
          </div>
          <div className="exportStatusCard">
            <p>任务状态</p>
            <strong>{TASK_STATUS_LABELS[task.status] || task.status}</strong>
            <span>导出时间：{formatDate(exportedAt)}</span>
          </div>
        </header>

        <section className="exportSection">
          <h2>工单与设备信息</h2>
          <div className="exportMetaGrid">
            <div className="exportMetaItem">
              <span>工单编号</span>
              <strong>{task.work_order_id || "未填写"}</strong>
            </div>
            <div className="exportMetaItem">
              <span>设备编号</span>
              <strong>{task.asset_code || "未填写"}</strong>
            </div>
            <div className="exportMetaItem">
              <span>报修来源</span>
              <strong>{task.report_source || "未填写"}</strong>
            </div>
            <div className="exportMetaItem">
              <span>工单优先级</span>
              <strong>{PRIORITY_LABELS[task.priority || "medium"] || task.priority || "中"}</strong>
            </div>
            <div className="exportMetaItem">
              <span>设备类型</span>
              <strong>{task.equipment_type}</strong>
            </div>
            <div className="exportMetaItem">
              <span>设备型号</span>
              <strong>{task.equipment_model || "未填写"}</strong>
            </div>
            <div className="exportMetaItem">
              <span>检修模式</span>
              <strong>{MAINTENANCE_LEVEL_LABELS[task.maintenance_level] || task.maintenance_level}</strong>
            </div>
            <div className="exportMetaItem">
              <span>故障类型</span>
              <strong>{task.fault_type || "未填写"}</strong>
            </div>
            <div className="exportMetaItem">
              <span>创建时间</span>
              <strong>{formatDate(task.created_at)}</strong>
            </div>
            <div className="exportMetaItem">
              <span>最后更新</span>
              <strong>{formatDate(task.updated_at)}</strong>
            </div>
          </div>
        </section>

        <section className="exportSection">
          <h2>任务摘要</h2>
          {task.symptom_description ? (
            <div className="exportBlock">
              <h3>故障现象</h3>
              <p>{task.symptom_description}</p>
            </div>
          ) : null}
          {task.advice_card ? (
            <div className="exportBlock">
              <h3>智能建议</h3>
              <p>{task.advice_card}</p>
            </div>
          ) : null}
          {exportSummary ? (
            <div className="exportBlock">
              <h3>导出摘要</h3>
              <p>{exportSummary}</p>
            </div>
          ) : null}
        </section>

        <section className="exportSection">
          <h2>结构化作业步骤</h2>
          <div className="exportStepList">
            {task.steps.map((step) => (
              <article key={step.id} className="exportStepCard">
                <div className="exportStepHeader">
                  <div>
                    <p className="eyebrow">STEP {step.step_order}</p>
                    <h3>{step.title}</h3>
                  </div>
                  <div className="exportStepMeta">
                    <span>{TASK_STATUS_LABELS[step.status] || step.status}</span>
                    <span>{step.estimated_minutes ? `约 ${step.estimated_minutes} 分钟` : "耗时待补充"}</span>
                  </div>
                </div>
                <p>{step.instruction}</p>
                <div className="exportInlineGrid">
                  <div className="exportInlineItem">
                    <span>工具</span>
                    <strong>{step.required_tools.length ? step.required_tools.join(" / ") : "未指定"}</strong>
                  </div>
                  <div className="exportInlineItem">
                    <span>材料</span>
                    <strong>
                      {step.required_materials.length ? step.required_materials.join(" / ") : "未指定"}
                    </strong>
                  </div>
                </div>
                {step.risk_warning ? (
                  <p className="exportWarning">风险提醒：{step.risk_warning}</p>
                ) : null}
                {step.caution ? <p className="exportMuted">注意事项：{step.caution}</p> : null}
                {step.confirmation_text ? <p className="exportMuted">确认动作：{step.confirmation_text}</p> : null}
                <div className="exportInlineGrid">
                  <div className="exportInlineItem">
                    <span>执行备注</span>
                    <strong>{step.completion_note || "未填写"}</strong>
                  </div>
                  <div className="exportInlineItem">
                    <span>完成时间</span>
                    <strong>{formatDate(step.completed_at)}</strong>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="exportSection">
          <h2>知识依据与来源</h2>
          {task.source_refs.length ? (
            <div className="exportReferenceList">
              {task.source_refs.map((ref) => (
                <article key={ref.chunk_id} className="exportReferenceCard">
                  <h3>{ref.title}</h3>
                  <p>
                    {ref.source_name} · {ref.section_reference || "章节待补充"} ·{" "}
                    {ref.page_reference || "页码待补充"}
                  </p>
                  <p>{ref.excerpt}</p>
                </article>
              ))}
            </div>
          ) : (
            <p className="exportMuted">当前任务未绑定明确知识引用。</p>
          )}
        </section>

        <section className="exportSection">
          <h2>签字确认</h2>
          <div className="exportSignatureGrid">
            <div className="exportSignatureItem">
              <span>执行人</span>
              <div className="signatureLine" />
            </div>
            <div className="exportSignatureItem">
              <span>复核人</span>
              <div className="signatureLine" />
            </div>
            <div className="exportSignatureItem">
              <span>班组确认</span>
              <div className="signatureLine" />
            </div>
          </div>
        </section>
      </article>
    </div>
  );
}
