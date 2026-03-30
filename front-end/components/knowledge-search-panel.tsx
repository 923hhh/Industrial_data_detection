"use client";

import { useMemo, useState } from "react";

import { searchKnowledge } from "@/lib/api";
import type { KnowledgeSearchResponse } from "@/lib/types";

export function KnowledgeSearchPanel() {
  const [query, setQuery] = useState("火花塞");
  const [equipmentType, setEquipmentType] = useState("摩托车发动机");
  const [equipmentModel, setEquipmentModel] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<KnowledgeSearchResponse | null>(null);

  const effectiveKeywords = useMemo(() => result?.effective_keywords ?? [], [result]);

  async function toBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const output = String(reader.result || "");
        const normalized = output.includes(",") ? output.split(",", 2)[1] : output;
        resolve(normalized);
      };
      reader.onerror = () => reject(new Error("图片读取失败"));
      reader.readAsDataURL(file);
    });
  }

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      const imageBase64 = imageFile ? await toBase64(imageFile) : null;
      const payload = await searchKnowledge({
        query,
        equipment_type: equipmentType || null,
        equipment_model: equipmentModel || null,
        image_base64: imageBase64,
        image_mime_type: imageFile?.type || null,
        image_filename: imageFile?.name || null,
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
        <label>
          <span>故障图片</span>
          <input
            className="fileInput"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={(event) => {
              const nextFile = event.target.files?.[0] ?? null;
              setImageFile(nextFile);
              setImagePreviewUrl(nextFile ? URL.createObjectURL(nextFile) : null);
            }}
          />
        </label>
      </div>
      {imagePreviewUrl ? (
        <div className="imagePreviewCard">
          <img src={imagePreviewUrl} alt="故障图片预览" className="thumbnailPreview" />
          <p className="muted">已选择图片：{imageFile?.name}</p>
        </div>
      ) : null}
      <div className="buttonRow">
        <button onClick={handleSubmit} disabled={loading}>
          {loading ? "检索中..." : "检索知识"}
        </button>
        {imageFile ? (
          <button
            type="button"
            onClick={() => {
              setImageFile(null);
              setImagePreviewUrl(null);
            }}
          >
            清除图片
          </button>
        ) : null}
      </div>
      {error ? <p className="errorText">{error}</p> : null}
      {result ? (
        <div className="resultGrid">
          <div className="infoStrip">
            <span>有效检索词：</span>
            {effectiveKeywords.length ? effectiveKeywords.join(" / ") : "无"}
          </div>
          {result.image_analysis ? (
            <article className="resultCard">
              <div className="resultMeta">
                <h3>图片识别结果</h3>
                <p>
                  {result.image_analysis.source === "vision_model" ? "视觉模型" : "回退模式"} ·{" "}
                  {result.image_analysis.keywords.join(" / ") || "无关键词"}
                </p>
              </div>
              <p className="excerpt">{result.image_analysis.summary}</p>
              {result.image_analysis.warning ? (
                <p className="errorText">{result.image_analysis.warning}</p>
              ) : null}
            </article>
          ) : null}
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
