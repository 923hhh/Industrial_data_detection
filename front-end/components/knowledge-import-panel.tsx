"use client";

import { useState } from "react";

import { importKnowledgePdf } from "@/lib/api";
import type { KnowledgeImportJobResponse } from "@/lib/types";

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
  const [error, setError] = useState<string | null>(null);
  const [job, setJob] = useState<KnowledgeImportJobResponse | null>(null);

  async function handleSubmit() {
    if (!file) {
      setError("请先选择一个 PDF 手册文件。");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("equipment_type", equipmentType);
    if (title.trim()) formData.append("title", title.trim());
    if (equipmentModel.trim()) formData.append("equipment_model", equipmentModel.trim());
    if (faultType.trim()) formData.append("fault_type", faultType.trim());
    if (sectionReference.trim()) formData.append("section_reference", sectionReference.trim());
    formData.append("replace_existing", String(replaceExisting));

    setLoading(true);
    setError(null);
    try {
      const payload = await importKnowledgePdf(formData);
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
            accept="application/pdf"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <label>
          <span>文档标题</span>
          <input value={title} onChange={(event) => setTitle(event.target.value)} />
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
          <span>故障类型</span>
          <input value={faultType} onChange={(event) => setFaultType(event.target.value)} />
        </label>
        <label>
          <span>章节说明</span>
          <input
            value={sectionReference}
            onChange={(event) => setSectionReference(event.target.value)}
          />
        </label>
      </div>
      <label className="toggleRow">
        <input
          type="checkbox"
          checked={replaceExisting}
          onChange={(event) => setReplaceExisting(event.target.checked)}
        />
        <span>存在同名文档时覆盖导入</span>
      </label>
      <div className="buttonRow">
        <button onClick={handleSubmit} disabled={loading}>
          {loading ? "导入中..." : "上传并导入 PDF"}
        </button>
      </div>
      {error ? <p className="errorText">{error}</p> : null}
      {job ? (
        <div className="resultCard">
          <div className="resultMeta">
            <h3>{job.title || job.source_name}</h3>
            <p>
              任务 #{job.id} · {job.status} · {job.page_count ?? 0} 页 / {job.chunk_count ?? 0} 段
            </p>
          </div>
          {job.preview_excerpt ? <p className="excerpt">{job.preview_excerpt}</p> : null}
          {job.error_message ? <p className="errorText">{job.error_message}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
