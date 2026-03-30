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

      <SectionCard title="最近案例" description="当前先接案例列表接口，后续再补上传、修正和审核面板。">
        <div className="tableCard">
          <table>
            <thead>
              <tr>
                <th>案例标题</th>
                <th>状态</th>
                <th>关联任务</th>
              </tr>
            </thead>
            <tbody>
              {(payload?.cases ?? []).map((item) => (
                <tr key={item.id}>
                  <td>{item.title}</td>
                  <td>{item.status}</td>
                  <td>{item.task_id ?? "无"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  );
}

