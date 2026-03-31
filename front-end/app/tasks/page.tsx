import Link from "next/link";

import { SectionCard } from "@/components/section-card";
import { getTaskHistory } from "@/lib/api";

type TasksPageProps = {
  searchParams: Promise<{
    status?: string;
    priority?: string;
    workOrderId?: string;
    limit?: string;
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

export default async function TasksPage({ searchParams }: TasksPageProps) {
  const { status, priority, workOrderId, limit } = await searchParams;
  const parsedLimit = Number(limit);
  const finalLimit = Number.isFinite(parsedLimit) && parsedLimit > 0 ? Math.min(parsedLimit, 50) : 20;
  const payload = await getTaskHistory({
    limit: finalLimit,
    status,
    priority,
    work_order_id: workOrderId,
  });
  const tasks = payload?.tasks ?? [];
  const inProgressCount = tasks.filter((task) => task.status === "in_progress").length;
  const completedCount = tasks.filter((task) => task.status === "completed").length;
  const urgentCount = tasks.filter((task) => task.priority === "urgent").length;

  return (
    <div className="page">
      <section className="hero">
        <p className="eyebrow">Task Center</p>
        <h2>检修任务中心</h2>
        <p>这里承接由知识引用驱动的标准化检修任务、步骤状态和导出结果。</p>
      </section>

      <SectionCard
        title="任务运营筛选"
        description="按工单编号、优先级和执行状态快速定位正式任务，适合比赛演示时展示任务运营视角。"
      >
        <form className="formGrid compactFormGrid">
          <label>
            <span>工单编号</span>
            <input name="workOrderId" defaultValue={workOrderId || ""} placeholder="支持模糊检索" />
          </label>
          <label>
            <span>任务状态</span>
            <select name="status" defaultValue={status || ""}>
              <option value="">全部状态</option>
              <option value="pending">待执行</option>
              <option value="in_progress">执行中</option>
              <option value="completed">已完成</option>
              <option value="skipped">已跳过</option>
            </select>
          </label>
          <label>
            <span>工单优先级</span>
            <select name="priority" defaultValue={priority || ""}>
              <option value="">全部优先级</option>
              <option value="low">低</option>
              <option value="medium">中</option>
              <option value="high">高</option>
              <option value="urgent">紧急</option>
            </select>
          </label>
          <label>
            <span>返回数量</span>
            <select name="limit" defaultValue={String(finalLimit)}>
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="30">30</option>
              <option value="50">50</option>
            </select>
          </label>
          <div className="buttonRow">
            <button type="submit">应用筛选</button>
            <Link href="/tasks" className="inlineActionLink">
              重置
            </Link>
          </div>
        </form>

        <div className="summaryGrid">
          <article className="resultCard">
            <h3>当前结果</h3>
            <p>{tasks.length} 个任务</p>
          </article>
          <article className="resultCard">
            <h3>执行中</h3>
            <p>{inProgressCount} 个任务</p>
          </article>
          <article className="resultCard">
            <h3>已完成</h3>
            <p>{completedCount} 个任务</p>
          </article>
          <article className="resultCard">
            <h3>紧急工单</h3>
            <p>{urgentCount} 个任务</p>
          </article>
        </div>
      </SectionCard>

      <SectionCard
        title="正式任务列表"
        description="任务中心已升级为可筛选的业务列表，支持按工单追踪执行进度并直接进入详情执行页。"
      >
        <div className="tableCard">
          <div className="tableSummary">
            <span>当前记录：{tasks.length}</span>
            {workOrderId ? <span>工单过滤：{workOrderId}</span> : null}
            {status ? <span>状态过滤：{TASK_STATUS_LABELS[status] || status}</span> : null}
            {priority ? <span>优先级过滤：{PRIORITY_LABELS[priority] || priority}</span> : null}
          </div>
          <table>
            <thead>
              <tr>
                <th>任务标题</th>
                <th>工单 / 设备</th>
                <th>优先级</th>
                <th>状态</th>
                <th>进度</th>
                <th>来源</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.id}>
                  <td>{task.title}</td>
                  <td>
                    {task.work_order_id || "未绑定工单"}
                    <br />
                    {task.asset_code || task.equipment_model || task.equipment_type}
                  </td>
                  <td>{PRIORITY_LABELS[task.priority || "medium"] || task.priority || "中"}</td>
                  <td>{TASK_STATUS_LABELS[task.status] || task.status}</td>
                  <td>
                    {task.completed_steps}/{task.total_steps}
                  </td>
                  <td>{task.report_source || "未填写"}</td>
                  <td>
                    <Link href={`/tasks/${task.id}`} className="inlineActionLink">
                      进入执行
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!tasks.length ? <p className="muted">当前筛选条件下暂无任务记录。</p> : null}
      </SectionCard>
    </div>
  );
}
