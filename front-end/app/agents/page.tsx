import { AgentAssistPanel } from "@/components/agent-assist-panel";
import { SectionCard } from "@/components/section-card";

export default function AgentsPage() {
  return (
    <div className="page">
      <section className="hero">
        <p className="eyebrow">Agent Orchestration</p>
        <h2>Agent 协作过程面板</h2>
        <p>这里是答辩时展示“不是一个模型做完所有事，而是多智能体协作完成整条链路”的核心页面。</p>
      </section>

      <SectionCard
        title="统一协作入口"
        description="当前会联合触发知识召回、作业规划、风险校验和案例沉淀建议，并返回可视化协作结果。"
      >
        <AgentAssistPanel />
      </SectionCard>
    </div>
  );
}
