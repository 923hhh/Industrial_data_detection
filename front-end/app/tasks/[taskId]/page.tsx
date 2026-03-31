import { notFound } from "next/navigation";

import { TaskExecutionPanel } from "@/components/task-execution-panel";
import { getMaintenanceTask, getMaintenanceTaskExport } from "@/lib/api";

type TaskDetailPageProps = {
  params: Promise<{
    taskId: string;
  }>;
};

export default async function TaskDetailPage({ params }: TaskDetailPageProps) {
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

  let exportSummary: string | null = null;
  try {
    const exported = await getMaintenanceTaskExport(numericTaskId);
    exportSummary = exported.export_summary;
  } catch {
    exportSummary = null;
  }

  return (
    <div className="page">
      <section className="hero">
        <p className="eyebrow">Task Execution</p>
        <h2>检修任务详情与执行页</h2>
        <p>这里承接 Agent 协作生成的正式任务，支持步骤执行、知识复核和任务摘要刷新。</p>
      </section>

      <TaskExecutionPanel initialTask={task} initialExportSummary={exportSummary} />
    </div>
  );
}
