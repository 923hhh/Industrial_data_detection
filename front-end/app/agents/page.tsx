import { AgentAssistPanel } from "@/components/agent-assist-panel";
import { StatCard } from "@/components/stat-card";
import { getWorkbenchOverview } from "@/lib/api";

export default async function AgentsPage() {
  const overview = await getWorkbenchOverview();

  return (
    <div className="page">
      <section className="hero">
        <p className="eyebrow">Agent Orchestration</p>
        <h2>多智能体检修协作中心</h2>
        <p>
          这里不再只是展示协作过程，而是把工单受理、知识依据锁定、作业预案、风险控制和案例回流整合成一页业务主链路。
        </p>
      </section>

      <div className="statsGrid">
        {(overview?.stats ?? []).map((item) => (
          <StatCard key={item.key} label={item.label} value={item.value} accent={item.accent} />
        ))}
      </div>

      <AgentAssistPanel
        featuredQueries={overview?.featured_queries ?? []}
        recentTasks={overview?.recent_tasks ?? []}
        recentCases={overview?.recent_cases ?? []}
      />
    </div>
  );
}
