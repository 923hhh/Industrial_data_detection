import Link from "next/link";

import { SectionCard } from "@/components/section-card";
import { getCases } from "@/lib/api";

type CasesPageProps = {
  searchParams: Promise<{
    status?: string;
    priority?: string;
    workOrderId?: string;
    limit?: string;
  }>;
};

const CASE_STATUS_LABELS: Record<string, string> = {
  pending_review: "待审核",
  approved: "已通过",
  rejected: "已驳回",
};

const PRIORITY_LABELS: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
  urgent: "紧急",
};

export default async function CasesPage({ searchParams }: CasesPageProps) {
  const { status, priority, workOrderId, limit } = await searchParams;
  const parsedLimit = Number(limit);
  const finalLimit = Number.isFinite(parsedLimit) && parsedLimit > 0 ? Math.min(parsedLimit, 50) : 20;
  const payload = await getCases({
    limit: finalLimit,
    status,
    priority,
    work_order_id: workOrderId,
  });
  const cases = payload?.cases ?? [];
  const pendingCount = cases.filter((item) => item.status === "pending_review").length;
  const approvedCount = cases.filter((item) => item.status === "approved").length;
  const tracedCount = cases.filter((item) => Boolean(item.source_document_id)).length;

  return (
    <div className="page">
      <section className="hero">
        <p className="eyebrow">Cases Center</p>
        <h2>案例沉淀与审核中心</h2>
        <p>案例页会成为“经验沉淀、人工修正、审核回流”的正式评审入口。</p>
      </section>

      <SectionCard
        title="案例运营筛选"
        description="按工单编号、优先级和审核状态快速定位案例，便于演示审核与知识回流链路。"
      >
        <form className="formGrid compactFormGrid">
          <label>
            <span>工单编号</span>
            <input name="workOrderId" defaultValue={workOrderId || ""} placeholder="支持模糊检索" />
          </label>
          <label>
            <span>审核状态</span>
            <select name="status" defaultValue={status || ""}>
              <option value="">全部状态</option>
              <option value="pending_review">待审核</option>
              <option value="approved">已通过</option>
              <option value="rejected">已驳回</option>
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
            <Link href="/cases" className="inlineActionLink">
              重置
            </Link>
          </div>
        </form>

        <div className="summaryGrid">
          <article className="resultCard">
            <h3>当前结果</h3>
            <p>{cases.length} 个案例</p>
          </article>
          <article className="resultCard">
            <h3>待审核</h3>
            <p>{pendingCount} 个案例</p>
          </article>
          <article className="resultCard">
            <h3>已通过</h3>
            <p>{approvedCount} 个案例</p>
          </article>
          <article className="resultCard">
            <h3>已绑定来源</h3>
            <p>{tracedCount} 个案例</p>
          </article>
        </div>
      </SectionCard>

      <SectionCard
        title="正式案例列表"
        description="案例中心已升级为可筛选的业务列表，支持从工单追踪到审核与来源回溯。"
      >
        <div className="tableCard">
          <div className="tableSummary">
            <span>当前记录：{cases.length}</span>
            {workOrderId ? <span>工单过滤：{workOrderId}</span> : null}
            {status ? <span>状态过滤：{CASE_STATUS_LABELS[status] || status}</span> : null}
            {priority ? <span>优先级过滤：{PRIORITY_LABELS[priority] || priority}</span> : null}
          </div>
          <table>
            <thead>
              <tr>
                <th>案例标题</th>
                <th>工单 / 设备</th>
                <th>优先级</th>
                <th>状态</th>
                <th>关联任务</th>
                <th>来源文档</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((item) => (
                <tr key={item.id}>
                  <td>{item.title}</td>
                  <td>
                    {item.work_order_id || "未绑定工单"}
                    <br />
                    {item.asset_code || item.equipment_model || item.equipment_type}
                  </td>
                  <td>{PRIORITY_LABELS[item.priority || "medium"] || item.priority || "中"}</td>
                  <td>{CASE_STATUS_LABELS[item.status] || item.status}</td>
                  <td>{item.task_id ?? "无"}</td>
                  <td>{item.source_document_id ? `#${item.source_document_id}` : "未回流"}</td>
                  <td>
                    <Link href={`/cases/${item.id}`} className="inlineActionLink">
                      查看详情
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!cases.length ? <p className="muted">当前筛选条件下暂无案例记录。</p> : null}

        <div className="buttonRow">
          <Link href="/cases/new" className="inlineActionLink">
            手动新建案例
          </Link>
        </div>
      </SectionCard>
    </div>
  );
}
