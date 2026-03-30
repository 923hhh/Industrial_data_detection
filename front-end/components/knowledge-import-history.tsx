"use client";

import { useEffect, useState } from "react";

import { getKnowledgeImportJobs } from "@/lib/api";
import type { KnowledgeImportJobResponse } from "@/lib/types";

type KnowledgeImportHistoryProps = {
  refreshToken?: number;
};

function renderStatus(status: string) {
  switch (status) {
    case "completed":
      return "已完成";
    case "failed":
      return "失败";
    case "processing":
      return "处理中";
    default:
      return status;
  }
}

export function KnowledgeImportHistory({ refreshToken = 0 }: KnowledgeImportHistoryProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<KnowledgeImportJobResponse[]>([]);

  useEffect(() => {
    void loadJobs();
  }, [refreshToken]);

  async function loadJobs() {
    setLoading(true);
    setError(null);
    try {
      const payload = await getKnowledgeImportJobs();
      setJobs(payload.jobs);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "导入记录加载失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panelStack">
      <div className="buttonRow">
        <button onClick={() => void loadJobs()} disabled={loading}>
          {loading ? "刷新中..." : "刷新导入记录"}
        </button>
      </div>
      {error ? <p className="errorText">{error}</p> : null}
      {!error && !jobs.length ? <p className="muted">当前还没有正式导入记录。</p> : null}
      <div className="historyList">
        {jobs.map((job) => (
          <article key={job.id} className="resultCard">
            <div className="resultMeta">
              <h3>{job.title || job.source_name}</h3>
              <p>
                任务 #{job.id} · {renderStatus(job.status)} · {job.page_count ?? 0} 页 /{" "}
                {job.chunk_count ?? 0} 段
              </p>
            </div>
            <p className="muted">
              {job.source_name} · {job.equipment_type}
              {job.equipment_model ? ` / ${job.equipment_model}` : ""}
            </p>
            {job.preview_excerpt ? <p className="excerpt">{job.preview_excerpt}</p> : null}
            {job.error_message ? <p className="errorText">{job.error_message}</p> : null}
          </article>
        ))}
      </div>
    </div>
  );
}
