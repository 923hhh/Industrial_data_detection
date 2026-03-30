"use client";

import { useEffect, useState } from "react";

import {
  getKnowledgeDocumentChunks,
  getKnowledgeDocumentDetail,
  getKnowledgeDocuments,
} from "@/lib/api";
import type {
  KnowledgeChunkPreview,
  KnowledgeDocumentDetailResponse,
  KnowledgeDocumentListItem,
} from "@/lib/types";

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
  const [selectedDocument, setSelectedDocument] = useState<KnowledgeDocumentDetailResponse | null>(null);
  const [chunks, setChunks] = useState<KnowledgeChunkPreview[]>([]);
  const [chunkLoading, setChunkLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [equipmentType, setEquipmentType] = useState("摩托车发动机");
  const [equipmentModel, setEquipmentModel] = useState("");
  const [sourceType, setSourceType] = useState("");

  useEffect(() => {
    void loadDocuments();
  }, [refreshToken]);

  useEffect(() => {
    if (!selectedDocumentId) {
      setChunks([]);
      setSelectedDocument(null);
      return;
    }
    void Promise.all([loadDocumentDetail(selectedDocumentId), loadChunks(selectedDocumentId)]);
  }, [selectedDocumentId]);

  async function loadDocuments() {
    setLoading(true);
    setError(null);
    try {
      const payload = await getKnowledgeDocuments({
        query,
        equipment_type: equipmentType,
        equipment_model: equipmentModel,
        source_type: sourceType,
      });
      setDocuments(payload.documents);
      setSelectedDocumentId((current) => {
        if (!payload.documents.length) return null;
        if (current && payload.documents.some((document) => document.id === current)) return current;
        return payload.documents[0]?.id ?? null;
      });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "文档列表加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadDocumentDetail(documentId: number) {
    try {
      const payload = await getKnowledgeDocumentDetail(documentId);
      setSelectedDocument(payload);
    } catch {
      setSelectedDocument(null);
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
      <div className="formGrid compactFormGrid">
        <label>
          <span>关键词</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="文档标题、来源或内容" />
        </label>
        <label>
          <span>设备类型</span>
          <input value={equipmentType} onChange={(event) => setEquipmentType(event.target.value)} />
        </label>
        <label>
          <span>设备型号</span>
          <input value={equipmentModel} onChange={(event) => setEquipmentModel(event.target.value)} placeholder="可留空查看通用手册" />
        </label>
        <label>
          <span>来源类型</span>
          <input value={sourceType} onChange={(event) => setSourceType(event.target.value)} placeholder="manual / case / procedure" />
        </label>
      </div>
      <div className="buttonRow">
        <button onClick={() => void loadDocuments()} disabled={loading}>
          {loading ? "刷新中..." : "刷新文档列表"}
        </button>
      </div>
      {error ? <p className="errorText">{error}</p> : null}
      <div className="libraryLayout">
        <div className="tableCard">
          <div className="tableSummary">
            <span>当前命中文档：{documents.length}</span>
            {selectedDocument ? <span>已选文档：#{selectedDocument.id}</span> : null}
          </div>
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
          {selectedDocument ? (
            <div className="resultCard">
              <div className="resultMeta">
                <h3>{selectedDocument.title}</h3>
                <p>
                  {selectedDocument.source_name} · {selectedDocument.source_type} ·{" "}
                  {selectedDocument.equipment_type}
                  {selectedDocument.equipment_model ? ` / ${selectedDocument.equipment_model}` : ""}
                </p>
              </div>
              <p className="muted">
                来源回溯：{selectedDocument.page_reference || "页码待补充"} ·{" "}
                {selectedDocument.section_reference || "章节待补充"} · 状态 {selectedDocument.status}
              </p>
              {selectedDocument.fault_type ? <p className="muted">故障类型：{selectedDocument.fault_type}</p> : null}
              {selectedDocument.content_excerpt ? <p className="excerpt">{selectedDocument.content_excerpt}</p> : null}
            </div>
          ) : null}
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
