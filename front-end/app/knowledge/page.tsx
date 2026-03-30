import { KnowledgeSearchPanel } from "@/components/knowledge-search-panel";
import { SectionCard } from "@/components/section-card";

export default function KnowledgePage() {
  return (
    <div className="page">
      <section className="hero">
        <p className="eyebrow">Knowledge Center</p>
        <h2>知识检索中心</h2>
        <p>这里承接正式检修场景中的知识查询、引用展示和后续作业步骤生成。</p>
      </section>

      <SectionCard
        title="正式检索入口"
        description="当前已接入正式知识检索 API，可直接验证 query rewrite、同义词扩展与通用手册命中。"
      >
        <KnowledgeSearchPanel />
      </SectionCard>
    </div>
  );
}

