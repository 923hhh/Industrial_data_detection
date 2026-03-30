import { KnowledgeManagementCenter } from "@/components/knowledge-management-center";

export default function KnowledgePage() {
  return (
    <div className="page">
      <section className="hero">
        <p className="eyebrow">Knowledge Center</p>
        <h2>知识检索中心</h2>
        <p>
          这里不再只是检索入口，而是正式知识管理中心：包含 PDF 手册导入、文档列表、分段预览、
          命中调试和正式检修知识检索。
        </p>
      </section>

      <KnowledgeManagementCenter />
    </div>
  );
}
