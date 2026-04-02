import { SectionCard } from "@/components/section-card";
import { StatCard } from "@/components/stat-card";
import { getWorkbenchOverview } from "@/lib/api";

export default async function HomePage() {
  const overview = await getWorkbenchOverview();

  return (
    <div className="page">
      <section className="hero">
        <p className="eyebrow">Next.js Front-end</p>
        <h2>软件杯正式工作台</h2>
        <p>
          这一版首页不再只是调试入口，而是围绕知识检索、标准化作业、案例沉淀和 Agent
          协作来组织正式产品信息架构。
        </p>
      </section>

      <div className="statsGrid">
        {(overview?.stats ?? []).map((item) => (
          <StatCard key={item.key} label={item.label} value={item.value} accent={item.accent} />
        ))}
      </div>

      <div className="twoGrid">
        <SectionCard title="固定检索词" description="正式演示和回归优先使用这些词条。">
          <ul className="simpleList">
            {(overview?.featured_queries ?? []).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </SectionCard>

        <SectionCard title="Agent 能力板" description="当前前台要显式呈现的多智能体角色。">
          <ul className="simpleList">
            {(overview?.agent_capabilities ?? []).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </SectionCard>
      </div>

      <div className="twoGrid">
        <SectionCard title="评测快照" description="固定评测集输出的正式指标，优先用于答辩和回归说明。">
          <div className="threeGrid">
            {(overview?.quality_highlights ?? []).map((item) => (
              <article key={item.key} className="resultCard">
                <p className="eyebrow">{item.label}</p>
                <h3>{item.value}</h3>
                {item.description ? <p className="muted">{item.description}</p> : null}
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="运行指标" description="当前进程内累计的关键业务指标，用于上线后快速验收。">
          <div className="threeGrid">
            {(overview?.runtime_highlights ?? []).map((item) => (
              <article key={item.key} className="resultCard">
                <p className="eyebrow">{item.label}</p>
                <h3>{item.value}</h3>
                {item.description ? <p className="muted">{item.description}</p> : null}
              </article>
            ))}
          </div>
        </SectionCard>
      </div>

      <div className="twoGrid">
        <SectionCard title="最近任务" description="标准化检修任务与进度摘要。">
          <div className="tableCard">
            <table>
              <thead>
                <tr>
                  <th>任务</th>
                  <th>状态</th>
                  <th>步骤进度</th>
                </tr>
              </thead>
              <tbody>
                {(overview?.recent_tasks ?? []).map((task) => (
                  <tr key={task.id}>
                    <td>{task.title}</td>
                    <td>{task.status}</td>
                    <td>
                      {task.completed_steps}/{task.total_steps}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <SectionCard title="最近案例" description="用于答辩展示的案例沉淀和审核状态。">
          <div className="tableCard">
            <table>
              <thead>
                <tr>
                  <th>案例</th>
                  <th>状态</th>
                  <th>设备</th>
                </tr>
              </thead>
              <tbody>
                {(overview?.recent_cases ?? []).map((item) => (
                  <tr key={item.id}>
                    <td>{item.title}</td>
                    <td>{item.status}</td>
                    <td>{item.equipment_model || item.equipment_type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
