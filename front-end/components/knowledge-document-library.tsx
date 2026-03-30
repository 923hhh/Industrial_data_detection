"use client";

import { useEffect, useState } from "react";

import { getKnowledgeDocumentChunks, getKnowledgeDocuments } from "@/lib/api";
import type { KnowledgeChunkPreview, KnowledgeDocumentListItem } from "@/lib/types";

type KnowledgeDocumentLibraryProps = {
  refreshToken?: number;
};

export function KnowledgeDocumentLibrary({
  refreshToken = 0,
}: KnowledgeDocumentLibraryProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocumentListItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [chunks, setChunks] = useState<KnowledgeChunkPreview[]>([]);
  const [chunkLoading, setChunkLoading] = useState(false);

  useEffect(() => {
    void loadDocuments();
  }, [refreshToken]);

  useEffect(() => {
    if (!selectedDocumentId) {
      setChunks([]);
      return;
    }
    void loadChunks(selectedDocumentId);
  }, [selectedDocumentId]);

  async function loadDocuments() {
    setLoading(true);
    setError(null);
    try {
      const payload = await getKnowledgeDocuments();
      setDocuments(payload.documents);
      setSelectedDocumentId((current) => current ?? payload.documents[0]?.id ?? null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "文档列表加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadChunks(documentId: number) {
    setChunkLoading(true);
    try {
      const payload = await getKnowledgeDocumentChunks(documentId);
      setChunks(payload.chunks);
    } catch {
      setChunks([]);
    } finally {
      setChunkLoading(false);
    }
  }

  return (
    <div className="panelStack">
      <div className="buttonRow">
        <button onClick={() => void loadDocuments()} disabled={loading}>
          {loading ? "刷新中..." : "刷新文档列表"}
        </button>
      </div>
      {error ? <p className="errorText">{error}</p> : null}
      <div className="libraryLayout">
        <div className="tableCard">
          <table>
            <thead>
              <tr>
                <th>文档</th>
                <th>来源</th>
                <th>分段</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((document) => (
                <tr
                  key={document.id}
                  className={selectedDocumentId === document.id ? "selectedRow" : undefined}
                  onClick={() => setSelectedDocumentId(document.id)}
                >
                  <td>{document.title}</td>
                  <td>{document.source_name}</td>
                  <td>{document.chunk_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="sectionCard chunkPreviewCard">
          <div className="sectionHeader">
            <h2>分段预览</h2>
            <p>用于导入验收和命中调试，查看当前文档的前几段知识内容。</p>
          </div>
          {chunkLoading ? <p className="muted">正在加载分段预览...</p> : null}
          {!chunkLoading && !chunks.length ? <p className="muted">当前文档暂无分段预览。</p> : null}
          <div className="chunkList">
            {chunks.map((chunk) => (
              <article key={chunk.chunk_id} className="resultCard">
                <div className="resultMeta">
                  <h3>{chunk.heading || `第 ${chunk.chunk_index} 段`}</h3>
                  <p>
                    {chunk.page_reference || "页码待补充"} · {chunk.section_reference || "章节待补充"}
                  </p>
                </div>
                <p className="excerpt">{chunk.content}</p>
              </article>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
