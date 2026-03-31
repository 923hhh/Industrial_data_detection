import { CaseSubmissionPanel } from "@/components/case-submission-panel";
import { getMaintenanceTask, getMaintenanceTaskExport } from "@/lib/api";

type CaseNewPageProps = {
  searchParams: Promise<{
    taskId?: string;
  }>;
};

export default async function NewCasePage({ searchParams }: CaseNewPageProps) {
  const { taskId } = await searchParams;
  const numericTaskId = Number(taskId);

  let task = null;
  let exportSummary: string | null = null;

  if (Number.isFinite(numericTaskId) && numericTaskId > 0) {
    try {
      task = await getMaintenanceTask(numericTaskId);
    } catch {
      task = null;
    }

    if (task) {
      try {
        const exported = await getMaintenanceTaskExport(numericTaskId);
        exportSummary = exported.export_summary;
      } catch {
        exportSummary = null;
      }
    }
  }

  return (
    <div className="page">
      <section className="hero">
        <p className="eyebrow">Case Submission</p>
        <h2>案例沉淀创建页</h2>
        <p>这里承接任务执行结果，生成待审核案例，并把经验、知识引用和处理总结沉淀到正式链路中。</p>
      </section>

      <CaseSubmissionPanel initialTask={task} initialExportSummary={exportSummary} />
    </div>
  );
}
