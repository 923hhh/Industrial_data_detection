import Link from "next/link";

import { SectionCard } from "@/components/section-card";
import { getCases } from "@/lib/api";

export default async function CasesPage() {
  const payload = await getCases(10);

  return (
    <div className="page">
      <section className="hero">
        <p className="eyebrow">Cases Center</p>
        <h2>案例沉淀与审核中心</h2>
        <p>案例页会成为“经验沉淀、人工修正、审核回流”的正式评审入口。</p>
      </section>

      <SectionCard
        title="最近案例"
        description="当前案例中心已支持详情查看、人工修正和审核操作，后续继续补更完整的筛选与统计。"
      >
        <div className="tableCard">
          <table>
            <thead>
              <tr>
                <th>案例标题</th>
                <th>状态</th>
                <th>关联任务</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {(payload?.cases ?? []).map((item) => (
                <tr key={item.id}>
                  <td>{item.title}</td>
                  <td>{item.status}</td>
                  <td>{item.task_id ?? "无"}</td>
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

        <div className="buttonRow">
          <Link href="/cases/new" className="inlineActionLink">
            手动新建案例
          </Link>
        </div>
      </SectionCard>
    </div>
  );
}
