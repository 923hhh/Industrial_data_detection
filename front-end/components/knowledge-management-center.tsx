"use client";

import { useState } from "react";

import type { KnowledgeImportJobResponse } from "@/lib/types";

import { KnowledgeDocumentLibrary } from "@/components/knowledge-document-library";
import { KnowledgeImportPanel } from "@/components/knowledge-import-panel";
import { KnowledgeSearchPanel } from "@/components/knowledge-search-panel";
import { SectionCard } from "@/components/section-card";

export function KnowledgeManagementCenter() {
  const [refreshToken, setRefreshToken] = useState(0);
  const [latestJob, setLatestJob] = useState<KnowledgeImportJobResponse | null>(null);

  function handleImported(job: KnowledgeImportJobResponse) {
    setLatestJob(job);
    setRefreshToken((current) => current + 1);
  }

  return (
    <div className="panelStack">
      <SectionCard
        title="文档导入管理"
        description="上传 PDF 手册并直接生成正式知识导入任务，完成页数、分段数和导入结果验收。"
      >
        <KnowledgeImportPanel onImported={handleImported} />
      </SectionCard>

      {latestJob ? (
        <SectionCard
          title="最近一次导入结果"
          description="正式知识中心会优先展示最近一次导入任务的状态，便于比赛演示时做验收说明。"
        >
          <div className="resultCard">
            <div className="resultMeta">
              <h3>{latestJob.title || latestJob.source_name}</h3>
              <p>
                任务 #{latestJob.id} · {latestJob.status} · 文档 {latestJob.document_id ?? "未生成"}
              </p>
            </div>
            {latestJob.preview_excerpt ? <p className="excerpt">{latestJob.preview_excerpt}</p> : null}
            {latestJob.error_message ? <p className="errorText">{latestJob.error_message}</p> : null}
          </div>
        </SectionCard>
      ) : null}

      <SectionCard
        title="正式检索入口"
        description="当前已接入 query rewrite、同义词扩展与通用手册命中逻辑，可直接验证知识检索主路径。"
      >
        <KnowledgeSearchPanel />
      </SectionCard>

      <SectionCard
        title="知识文档库与分段预览"
        description="查看已导入的正式知识文档、分段数和前几段内容，为命中调试与来源回溯服务。"
      >
        <KnowledgeDocumentLibrary refreshToken={refreshToken} />
      </SectionCard>
    </div>
  );
}
