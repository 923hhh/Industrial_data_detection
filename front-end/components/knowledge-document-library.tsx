"use client";

import { useEffect, useState } from "react";

import {
  getKnowledgeDocumentChunks,
  getKnowledgeDocumentDetail,
  getKnowledgeDocuments,
} from "@/lib/api";
import { formatKnowledgeAnchor } from "@/lib/knowledge-anchors";
import type {
  KnowledgeChunkPreview,
  KnowledgeDocumentDetailResponse,
  KnowledgeDocumentListItem,
} from "@/lib/types";

type KnowledgeDocumentLibraryProps = {
  refreshToken?: number;
  initialDocumentId?: number | null;
  initialChunkId?: number | null;
  initialSourceType?: string;
};

export function KnowledgeDocumentLibrary({
  refreshToken = 0,
  initialDocumentId = null,
  initialChunkId = null,
  initialSourceType = "",
}: KnowledgeDocumentLibraryProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocumentListItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(initialDocumentId);
  const [focusedChunkId, setFocusedChunkId] = useState<number | null>(initialChunkId);
  const [selectedDocument, setSelectedDocument] = useState<KnowledgeDocumentDetailResponse | null>(null);
  const [chunks, setChunks] = useState<KnowledgeChunkPreview[]>([]);
  const [chunkLoading, setChunkLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [equipmentType, setEquipmentType] = useState("摩托车发动机");
  const [equipmentModel, setEquipmentModel] = useState("");
  const [sourceType, setSourceType] = useState(initialSourceType || "");

  useEffect(() => {
    void loadDocuments({
      preferredDocumentId: initialDocumentId,
      preferredSourceType: initialSourceType || "",
    });
  }, [refreshToken, initialDocumentId, initialSourceType]);

  useEffect(() => {
    setSelectedDocumentId(initialDocumentId);
  }, [initialDocumentId]);

  useEffect(() => {
    setFocusedChunkId(initialChunkId);
  }, [initialChunkId]);

  useEffect(() => {
    setSourceType(initialSourceType || "");
  }, [initialSourceType]);

  useEffect(() => {
    if (!selectedDocumentId) {
      setChunks([]);
      setSelectedDocument(null);
      return;
    }
    void Promise.all([loadDocumentDetail(selectedDocumentId), loadChunks(selectedDocumentId, focusedChunkId)]);
  }, [selectedDocumentId, focusedChunkId]);

  useEffect(() => {
    if (!focusedChunkId) return;
    if (!chunks.some((chunk) => chunk.chunk_id === focusedChunkId)) return;
    const timer = window.setTimeout(() => {
      document.getElementById(`knowledge-chunk-${focusedChunkId}`)?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }, 80);
    return () => window.clearTimeout(timer);
  }, [chunks, focusedChunkId]);

  async function loadDocuments(options?: {
    preferredDocumentId?: number | null;
    preferredSourceType?: string;
  }) {
    setLoading(true);
    setError(null);
    try {
      const preferredSourceType = options?.preferredSourceType ?? sourceType;
      const preferredDocumentId =
        options?.preferredDocumentId !== undefined
          ? options.preferredDocumentId
          : selectedDocumentId || initialDocumentId;
      const payload = await getKnowledgeDocuments({
        query,
        equipment_type: equipmentType,
        equipment_model: equipmentModel,
        source_type: preferredSourceType,
        limit: preferredDocumentId ? 24 : 12,
      });

      let nextDocuments = payload.documents;

      if (preferredDocumentId && !nextDocuments.some((document) => document.id === preferredDocumentId)) {
        try {
          const focusedDocument = await getKnowledgeDocumentDetail(preferredDocumentId);
          nextDocuments = [focusedDocument, ...nextDocuments];
        } catch {
          // Ignore focus failures and keep the fetched list.
        }
      }

      setDocuments(nextDocuments);
      setSelectedDocumentId((current) => {
        if (!nextDocuments.length) return null;
        if (preferredDocumentId && nextDocuments.some((document) => document.id === preferredDocumentId)) {
          return preferredDocumentId;
        }
        if (current && nextDocuments.some((document) => document.id === current)) return current;
        return nextDocuments[0]?.id ?? null;
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

  async function loadChunks(documentId: number, nextFocusedChunkId?: number | null) {
    setChunkLoading(true);
    try {
      const payload = await getKnowledgeDocumentChunks(
        documentId,
        nextFocusedChunkId ? 8 : 6,
        nextFocusedChunkId,
      );
      setChunks(payload.chunks);
    } catch {
      setChunks([]);
    } finally {
      setChunkLoading(false);
    }
  }

  const focusedChunk = focusedChunkId
    ? chunks.find((chunk) => chunk.chunk_id === focusedChunkId) ?? null
    : null;

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
            {initialDocumentId ? <span>来源回溯模式</span> : null}
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
                  onClick={() => {
                    setSelectedDocumentId(document.id);
                    setFocusedChunkId(null);
                  }}
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
              {focusedChunk ? (
                <p className="muted">当前定位：{formatKnowledgeAnchor(focusedChunk)}</p>
              ) : null}
              {selectedDocument.fault_type ? <p className="muted">故障类型：{selectedDocument.fault_type}</p> : null}
              {selectedDocument.content_excerpt ? <p className="excerpt">{selectedDocument.content_excerpt}</p> : null}
            </div>
          ) : null}
          {chunkLoading ? <p className="muted">正在加载分段预览...</p> : null}
          {!chunkLoading && !chunks.length ? <p className="muted">当前文档暂无分段预览。</p> : null}
          <div className="chunkList">
            {chunks.map((chunk) => (
              <article
                key={chunk.chunk_id}
                id={`knowledge-chunk-${chunk.chunk_id}`}
                className={`resultCard ${focusedChunkId === chunk.chunk_id ? "focusedCard" : ""}`}
              >
                <div className="resultMeta">
                  <h3>{chunk.heading || `第 ${chunk.chunk_index} 段`}</h3>
                  <p>{formatKnowledgeAnchor(chunk)}</p>
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
