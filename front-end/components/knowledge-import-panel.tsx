"use client";

import { useState } from "react";

import { importKnowledgePdf, previewKnowledgeImport } from "@/lib/api";
import type { KnowledgeImportJobResponse, KnowledgeImportPreviewResponse } from "@/lib/types";

type KnowledgeImportPanelProps = {
  onImported?: (job: KnowledgeImportJobResponse) => void;
};

export function KnowledgeImportPanel({ onImported }: KnowledgeImportPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [equipmentType, setEquipmentType] = useState("摩托车发动机");
  const [equipmentModel, setEquipmentModel] = useState("");
  const [faultType, setFaultType] = useState("");
  const [sectionReference, setSectionReference] = useState("");
  const [replaceExisting, setReplaceExisting] = useState(true);
  const [loading, setLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<KnowledgeImportPreviewResponse | null>(null);
  const [job, setJob] = useState<KnowledgeImportJobResponse | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);

  function resetDerivedState() {
    setPreview(null);
    setJob(null);
    setError(null);
  }

  function buildFormData() {
    if (!file) {
      throw new Error("请先选择一个 PDF 手册文件。");
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("equipment_type", equipmentType);
    if (title.trim()) formData.append("title", title.trim());
    if (equipmentModel.trim()) formData.append("equipment_model", equipmentModel.trim());
    if (faultType.trim()) formData.append("fault_type", faultType.trim());
    if (sectionReference.trim()) formData.append("section_reference", sectionReference.trim());
    formData.append("replace_existing", String(replaceExisting));
    return formData;
  }

  async function handlePreview() {
    setPreviewLoading(true);
    setError(null);
    setJob(null);
    try {
      const payload = await previewKnowledgeImport(buildFormData());
      setPreview(payload);
    } catch (previewError) {
      setPreview(null);
      setError(previewError instanceof Error ? previewError.message : "导入预览失败");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      const payload = await importKnowledgePdf(buildFormData());
      setJob(payload);
      onImported?.(payload);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "PDF 导入失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panelStack">
      <div className="formGrid">
        <label>
          <span>PDF 手册文件</span>
          <input
            className="fileInput"
            type="file"
            accept="application/pdf,image/png,image/jpeg,image/webp"
            onChange={(event) => {
              const nextFile = event.target.files?.[0] ?? null;
              setFile(nextFile);
              setImagePreviewUrl(
                nextFile && nextFile.type.startsWith("image/") ? URL.createObjectURL(nextFile) : null,
              );
              resetDerivedState();
            }}
          />
        </label>
        <label>
          <span>文档标题</span>
          <input
            value={title}
            onChange={(event) => {
              setTitle(event.target.value);
              resetDerivedState();
            }}
          />
        </label>
        <label>
          <span>设备类型</span>
          <input
            value={equipmentType}
            onChange={(event) => {
              setEquipmentType(event.target.value);
              resetDerivedState();
            }}
          />
        </label>
        <label>
          <span>设备型号</span>
          <input
            value={equipmentModel}
            onChange={(event) => {
              setEquipmentModel(event.target.value);
              resetDerivedState();
            }}
          />
        </label>
        <label>
          <span>故障类型</span>
          <input
            value={faultType}
            onChange={(event) => {
              setFaultType(event.target.value);
              resetDerivedState();
            }}
          />
        </label>
        <label>
          <span>章节说明</span>
          <input
            value={sectionReference}
            onChange={(event) => {
              setSectionReference(event.target.value);
              resetDerivedState();
            }}
          />
        </label>
      </div>
      {imagePreviewUrl ? (
        <div className="imagePreviewCard">
          <img src={imagePreviewUrl} alt="知识导入图片预览" className="thumbnailPreview" />
          <p className="muted">当前图片将按 OCR 导入流程处理：{file?.name}</p>
        </div>
      ) : null}
      <label className="toggleRow">
        <input
          type="checkbox"
          checked={replaceExisting}
          onChange={(event) => {
            setReplaceExisting(event.target.checked);
            resetDerivedState();
          }}
        />
        <span>存在同名文档时覆盖导入</span>
      </label>
      <div className="buttonRow">
        <button onClick={handlePreview} disabled={previewLoading || loading}>
          {previewLoading ? "预览生成中..." : "生成导入预览"}
        </button>
        <button onClick={handleSubmit} disabled={loading || !preview}>
          {loading ? "导入中..." : "确认导入 PDF"}
        </button>
      </div>
      {error ? <p className="errorText">{error}</p> : null}
      {preview ? (
        <div className="resultCard">
          <div className="resultMeta">
            <h3>{preview.normalized_title}</h3>
            <p>
              {preview.import_type === "pdf" ? "PDF 预览" : "图片导入预览"} · {preview.page_count} 页 / {preview.chunk_count} 段 ·{" "}
              {preview.equipment_model || "通用手册"}
            </p>
          </div>
          {preview.processing_note ? <p className="muted">{preview.processing_note}</p> : null}
          {preview.preview_excerpt ? <p className="excerpt">{preview.preview_excerpt}</p> : null}
          {preview.warning_message ? <p className="errorText">{preview.warning_message}</p> : null}
        </div>
      ) : null}
      {job ? (
        <div className="resultCard">
          <div className="resultMeta">
            <h3>{job.title || job.source_name}</h3>
            <p>
              任务 #{job.id} · {job.import_type} · {job.status} · {job.page_count ?? 0} 页 / {job.chunk_count ?? 0} 段
            </p>
          </div>
          {job.processing_note ? <p className="muted">{job.processing_note}</p> : null}
          {job.preview_excerpt ? <p className="excerpt">{job.preview_excerpt}</p> : null}
          {job.error_message ? <p className="errorText">{job.error_message}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
