"use client";

import { useMemo, useState } from "react";

import { searchKnowledge } from "@/lib/api";
import type { KnowledgeSearchResponse } from "@/lib/types";

export function KnowledgeSearchPanel() {
  const [query, setQuery] = useState("火花塞");
  const [equipmentType, setEquipmentType] = useState("摩托车发动机");
  const [equipmentModel, setEquipmentModel] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<KnowledgeSearchResponse | null>(null);

  const effectiveKeywords = useMemo(() => result?.effective_keywords ?? [], [result]);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      const payload = await searchKnowledge({
        query,
        equipment_type: equipmentType || null,
        equipment_model: equipmentModel || null,
        limit: 5,
      });
      setResult(payload);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "知识检索失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panelStack">
      <div className="formGrid">
        <label>
          <span>检索问题</span>
          <textarea value={query} onChange={(event) => setQuery(event.target.value)} rows={4} />
        </label>
        <label>
          <span>设备类型</span>
          <input value={equipmentType} onChange={(event) => setEquipmentType(event.target.value)} />
        </label>
        <label>
          <span>设备型号</span>
          <input value={equipmentModel} onChange={(event) => setEquipmentModel(event.target.value)} />
        </label>
      </div>
      <div className="buttonRow">
        <button onClick={handleSubmit} disabled={loading}>
          {loading ? "检索中..." : "检索知识"}
        </button>
      </div>
      {error ? <p className="errorText">{error}</p> : null}
      {result ? (
        <div className="resultGrid">
          <div className="infoStrip">
            <span>有效检索词：</span>
            {effectiveKeywords.length ? effectiveKeywords.join(" / ") : "无"}
          </div>
          {result.results.length ? (
            result.results.map((item) => (
              <article key={item.chunk_id} className="resultCard">
                <div className="resultMeta">
                  <h3>{item.title}</h3>
                  <p>
                    {item.source_name} · {item.page_reference ?? "页码待补充"}
                  </p>
                </div>
                <p className="excerpt">{item.excerpt}</p>
                <p className="reason">{item.recommendation_reason}</p>
              </article>
            ))
          ) : (
            <p className="muted">当前条件下暂无命中结果。</p>
          )}
        </div>
      ) : null}
    </div>
  );
}

