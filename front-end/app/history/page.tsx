import { SectionCard } from "@/components/section-card";
import { getCases, getTaskHistory } from "@/lib/api";

export default async function HistoryPage() {
  const [tasks, cases] = await Promise.all([getTaskHistory(20), getCases(20)]);

  return (
    <div className="page">
      <section className="hero">
        <p className="eyebrow">History Center</p>
        <h2>历史记录与导出入口</h2>
        <p>这个页面用于统一回看任务执行与案例沉淀记录，后续会补结果导出和时间线。</p>
      </section>

      <div className="twoGrid">
        <SectionCard title="任务历史">
          <ul className="simpleList">
            {(tasks?.tasks ?? []).map((item) => (
              <li key={item.id}>
                {item.title} · {item.status} · {item.completed_steps}/{item.total_steps}
              </li>
            ))}
          </ul>
        </SectionCard>

        <SectionCard title="案例历史">
          <ul className="simpleList">
            {(cases?.cases ?? []).map((item) => (
              <li key={item.id}>
                {item.title} · {item.status} · {item.equipment_model || item.equipment_type}
              </li>
            ))}
          </ul>
        </SectionCard>
      </div>
    </div>
  );
}

