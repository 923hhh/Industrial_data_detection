"use client";

import { useState } from "react";

import type { KnowledgeImportJobResponse } from "@/lib/types";

import { KnowledgeDocumentLibrary } from "@/components/knowledge-document-library";
import { KnowledgeImportHistory } from "@/components/knowledge-import-history";
import { KnowledgeImportPanel } from "@/components/knowledge-import-panel";
import { KnowledgeSearchPanel } from "@/components/knowledge-search-panel";
import { SectionCard } from "@/components/section-card";

type KnowledgeManagementCenterProps = {
  focusDocumentId?: number | null;
  focusChunkId?: number | null;
  initialSourceType?: string;
};

export function KnowledgeManagementCenter({
  focusDocumentId = null,
  focusChunkId = null,
  initialSourceType = "",
}: KnowledgeManagementCenterProps) {
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
        description="上传 PDF 手册或图片型知识文档并生成正式导入任务，支持 OCR 预览、页数/分段数验收与来源回溯。"
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
        title="导入记录列表"
        description="查看最近的正式知识导入任务，快速确认导入状态、页数、分段数和失败原因。"
      >
        <KnowledgeImportHistory refreshToken={refreshToken} />
      </SectionCard>

      <SectionCard
        title="正式检索入口"
        description="当前已接入 query rewrite、同义词扩展、通用手册命中和图片上传入口，可直接验证知识检索主路径。"
      >
        <KnowledgeSearchPanel />
      </SectionCard>

      <SectionCard
        title="知识文档库与分段预览"
        description="查看已导入的正式知识文档、分段数和前几段内容，为命中调试与来源回溯服务。"
      >
        <KnowledgeDocumentLibrary
          refreshToken={refreshToken}
          initialDocumentId={focusDocumentId}
          initialChunkId={focusChunkId}
          initialSourceType={initialSourceType}
        />
      </SectionCard>
    </div>
  );
}
