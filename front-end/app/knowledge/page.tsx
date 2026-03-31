import { KnowledgeManagementCenter } from "@/components/knowledge-management-center";

type KnowledgePageProps = {
  searchParams: Promise<{
    documentId?: string;
    sourceType?: string;
  }>;
};

export default async function KnowledgePage({ searchParams }: KnowledgePageProps) {
  const { documentId, sourceType } = await searchParams;
  const focusDocumentId = Number(documentId);

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

      <KnowledgeManagementCenter
        focusDocumentId={Number.isFinite(focusDocumentId) && focusDocumentId > 0 ? focusDocumentId : null}
        initialSourceType={sourceType || ""}
      />
    </div>
  );
}
