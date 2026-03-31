"use client";

import { startTransition, useState } from "react";
import { useRouter } from "next/navigation";

import { assistWithAgents, createMaintenanceTask, getAgentRun } from "@/lib/api";
import { SectionCard } from "@/components/section-card";
import type {
  AgentAssistResponse,
  WorkbenchCaseSummary,
  WorkbenchTaskSummary,
} from "@/lib/types";

type AgentAssistPanelProps = {
  featuredQueries: string[];
  recentTasks: WorkbenchTaskSummary[];
  recentCases: WorkbenchCaseSummary[];
};

type PriorityLevel = "low" | "medium" | "high" | "urgent";
type MaintenanceLevel = "routine" | "standard" | "emergency";

type IntakeDraft = {
  workOrderId: string;
  assetCode: string;
  reportSource: string;
  priority: PriorityLevel;
  maintenanceLevel: MaintenanceLevel;
  equipmentType: string;
  equipmentModel: string;
  faultType: string;
  query: string;
};

type ScenarioPreset = {
  label: string;
  workOrderId: string;
  assetCode: string;
  reportSource: string;
  priority: PriorityLevel;
  maintenanceLevel: MaintenanceLevel;
  equipmentType: string;
  equipmentModel: string;
  faultType: string;
  query: string;
};

const SCENARIO_PRESETS: ScenarioPreset[] = [
  {
    label: "冷启动困难",
    workOrderId: "WO-20260331-01",
    assetCode: "ENG-LX200-01",
    reportSource: "巡检上报",
    priority: "high",
    maintenanceLevel: "standard",
    equipmentType: "摩托车发动机",
    equipmentModel: "LX200",
    faultType: "启动困难",
    query: "发动机冷启动困难，伴随火花塞积碳，怠速不稳，现场反馈多次点火后才能启动。",
  },
  {
    label: "温度偏高",
    workOrderId: "WO-20260331-02",
    assetCode: "ENG-LX200-02",
    reportSource: "现场报修",
    priority: "urgent",
    maintenanceLevel: "emergency",
    equipmentType: "摩托车发动机",
    equipmentModel: "LX200",
    faultType: "温度偏高",
    query: "发动机温度偏高并伴随焦糊味，短时运行后机油渗漏风险上升，需要先做应急隔离。",
  },
  {
    label: "正时链条异响",
    workOrderId: "WO-20260331-03",
    assetCode: "ENG-LX150-03",
    reportSource: "定检发现",
    priority: "medium",
    maintenanceLevel: "routine",
    equipmentType: "摩托车发动机",
    equipmentModel: "LX150",
    faultType: "异响",
    query: "发动机运行中存在明显正时链条异响，低速工况更明显，需要按例行流程排查紧固与磨损状态。",
  },
];

const PRIORITY_LABELS: Record<PriorityLevel, string> = {
  low: "低",
  medium: "中",
  high: "高",
  urgent: "紧急",
};

const MAINTENANCE_LABELS: Record<MaintenanceLevel, string> = {
  routine: "例行检修",
  standard: "标准检修",
  emergency: "应急处置",
};

const EXECUTION_STATUS_LABELS: Record<string, string> = {
  ready: "可下发执行",
  review_required: "需人工复核",
  need_more_input: "待补充信息",
};

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

function formatDate(value?: string | null): string {
  if (!value) {
    return "时间待记录";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString("zh-CN", {
    hour12: false,
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getExecutionTone(status?: string | null): string {
  if (status === "ready") {
    return "status-ready";
  }
  if (status === "review_required") {
    return "status-review";
  }
  return "status-pending";
}

export function AgentAssistPanel({
  featuredQueries,
  recentTasks,
  recentCases,
}: AgentAssistPanelProps) {
  const router = useRouter();
  const [draft, setDraft] = useState<IntakeDraft>({
    workOrderId: SCENARIO_PRESETS[0].workOrderId,
    assetCode: SCENARIO_PRESETS[0].assetCode,
    reportSource: SCENARIO_PRESETS[0].reportSource,
    priority: SCENARIO_PRESETS[0].priority,
    maintenanceLevel: SCENARIO_PRESETS[0].maintenanceLevel,
    equipmentType: SCENARIO_PRESETS[0].equipmentType,
    equipmentModel: SCENARIO_PRESETS[0].equipmentModel,
    faultType: SCENARIO_PRESETS[0].faultType,
    query: SCENARIO_PRESETS[0].query,
  });
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [replayLoading, setReplayLoading] = useState(false);
  const [creatingTask, setCreatingTask] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AgentAssistResponse | null>(null);
  const [selectedChunkIds, setSelectedChunkIds] = useState<number[]>([]);
  const [replayRunId, setReplayRunId] = useState("");

  function applyPreset(preset: ScenarioPreset) {
    setDraft({
      workOrderId: preset.workOrderId,
      assetCode: preset.assetCode,
      reportSource: preset.reportSource,
      priority: preset.priority,
      maintenanceLevel: preset.maintenanceLevel,
      equipmentType: preset.equipmentType,
      equipmentModel: preset.equipmentModel,
      faultType: preset.faultType,
      query: preset.query,
    });
    setError(null);
    setSelectedChunkIds([]);
  }

  function toggleSelectedChunk(chunkId: number) {
    setSelectedChunkIds((current) =>
      current.includes(chunkId) ? current.filter((item) => item !== chunkId) : [...current, chunkId],
    );
  }

  async function handleRun(useSelectedKnowledge = false) {
    setLoading(true);
    setError(null);
    try {
      const imageBase64 = imageFile ? await toBase64(imageFile) : null;
      const payload = await assistWithAgents({
        work_order_id: draft.workOrderId || null,
        asset_code: draft.assetCode || null,
        report_source: draft.reportSource || null,
        priority: draft.priority,
        query: draft.query,
        equipment_type: draft.equipmentType || null,
        equipment_model: draft.equipmentModel || null,
        fault_type: draft.faultType || null,
        maintenance_level: draft.maintenanceLevel,
        selected_chunk_ids: useSelectedKnowledge ? selectedChunkIds : [],
        image_base64: imageBase64,
        image_mime_type: imageFile?.type || null,
        image_filename: imageFile?.name || null,
        limit: 6,
      });
      setResult(payload);
      setReplayRunId(payload.run_id);
      setSelectedChunkIds(payload.request_context?.selected_chunk_ids ?? []);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Agent 协作失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadRun() {
    if (!replayRunId.trim()) {
      setError("请输入需要回放的 Run ID。");
      return;
    }

    setReplayLoading(true);
    setError(null);
    try {
      const payload = await getAgentRun(replayRunId.trim());
      setResult(payload);
      setSelectedChunkIds(payload.request_context?.selected_chunk_ids ?? []);
      if (payload.request_context) {
        setDraft((current) => ({
          ...current,
          workOrderId: payload.request_context?.work_order_id || current.workOrderId,
          assetCode: payload.request_context?.asset_code || current.assetCode,
          reportSource: payload.request_context?.report_source || current.reportSource,
          priority: (payload.request_context?.priority as PriorityLevel) || current.priority,
          maintenanceLevel:
            (payload.request_context?.maintenance_level as MaintenanceLevel) || current.maintenanceLevel,
          equipmentType: payload.request_context?.equipment_type || current.equipmentType,
          equipmentModel: payload.request_context?.equipment_model || current.equipmentModel,
          faultType: payload.request_context?.fault_type || current.faultType,
          query: payload.request_context?.symptom_description || payload.effective_query || current.query,
        }));
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Run 回放失败");
    } finally {
      setReplayLoading(false);
    }
  }

  async function handleCreateTask() {
    if (!result) {
      setError("请先完成一次 Agent 协作，再创建正式任务。");
      return;
    }

    setCreatingTask(true);
    setError(null);
    try {
      const topKnowledge = result.knowledge_results[0];
      const equipmentType =
        result.request_context?.equipment_type || topKnowledge?.equipment_type || draft.equipmentType || "摩托车发动机";
      const equipmentModel =
        result.request_context?.equipment_model || topKnowledge?.equipment_model || draft.equipmentModel || null;
      const faultType =
        result.request_context?.fault_type || topKnowledge?.fault_type || draft.faultType || null;
      const symptomDescription =
        result.request_context?.symptom_description || result.effective_query || draft.query || null;
      const sourceChunkIds = selectedChunkIds.length
        ? selectedChunkIds
        : result.request_context?.selected_chunk_ids || [];

      const titlePrefix = result.request_context?.work_order_id
        ? `${result.request_context.work_order_id} · `
        : "";
      const title = `${titlePrefix}${equipmentModel || equipmentType}${
        faultType ? ` / ${faultType}` : ""
      }检修任务`;

      const payload = await createMaintenanceTask({
        title,
        work_order_id: result.request_context?.work_order_id || null,
        asset_code: result.request_context?.asset_code || null,
        report_source: result.request_context?.report_source || null,
        priority: result.request_context?.priority || draft.priority,
        equipment_type: equipmentType,
        equipment_model: equipmentModel,
        maintenance_level: result.request_context?.maintenance_level || draft.maintenanceLevel,
        fault_type: faultType,
        symptom_description: symptomDescription,
        source_chunk_ids: sourceChunkIds,
      });

      startTransition(() => {
        router.push(`/tasks/${payload.id}`);
      });
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "任务创建失败");
    } finally {
      setCreatingTask(false);
    }
  }

  return (
    <div className="panelStack">
      <div className="operationsLayout">
        <SectionCard
          title="工单受理与协作触发"
          description="先录入工单上下文，再触发 KnowledgeRetriever、WorkOrderPlanner、RiskControl 和 CaseCurator 四个 Agent。"
        >
          <div className="panelStack">
            <div className="presetGrid">
              {SCENARIO_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  className="secondaryButton"
                  onClick={() => applyPreset(preset)}
                >
                  {preset.label}
                </button>
              ))}
            </div>

            <div className="formGrid intakeGrid">
              <label>
                <span>工单编号</span>
                <input
                  value={draft.workOrderId}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, workOrderId: event.target.value }))
                  }
                />
              </label>
              <label>
                <span>设备编号</span>
                <input
                  value={draft.assetCode}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, assetCode: event.target.value }))
                  }
                />
              </label>
              <label>
                <span>报修来源</span>
                <input
                  value={draft.reportSource}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, reportSource: event.target.value }))
                  }
                />
              </label>
              <label>
                <span>工单优先级</span>
                <select
                  value={draft.priority}
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      priority: event.target.value as PriorityLevel,
                    }))
                  }
                >
                  {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>检修模式</span>
                <select
                  value={draft.maintenanceLevel}
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      maintenanceLevel: event.target.value as MaintenanceLevel,
                    }))
                  }
                >
                  {Object.entries(MAINTENANCE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>设备类型</span>
                <input
                  value={draft.equipmentType}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, equipmentType: event.target.value }))
                  }
                />
              </label>
              <label>
                <span>设备型号</span>
                <input
                  value={draft.equipmentModel}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, equipmentModel: event.target.value }))
                  }
                />
              </label>
              <label>
                <span>故障类型</span>
                <input
                  value={draft.faultType}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, faultType: event.target.value }))
                  }
                />
              </label>
              <label className="fullSpan">
                <span>现场异常描述</span>
                <textarea
                  value={draft.query}
                  onChange={(event) => setDraft((current) => ({ ...current, query: event.target.value }))}
                  rows={5}
                />
              </label>
              <label className="fullSpan">
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
              <button type="button" onClick={() => handleRun()} disabled={loading}>
                {loading ? "协作中..." : "触发多 Agent 协作"}
              </button>
              <button
                type="button"
                className="secondaryButton"
                onClick={() => handleRun(true)}
                disabled={loading || !selectedChunkIds.length}
              >
                按已锁定知识刷新预案
              </button>
              {imageFile ? (
                <button
                  type="button"
                  className="secondaryButton"
                  onClick={() => {
                    setImageFile(null);
                    setImagePreviewUrl(null);
                  }}
                >
                  清除图片
                </button>
              ) : null}
            </div>
          </div>
        </SectionCard>

        <SectionCard
          title="业务态势与运行回放"
          description="固定检索词、最近任务和最近案例会作为答辩时的业务背景板，Run ID 可直接回放历史协作结果。"
        >
          <div className="panelStack">
            <div className="tagRow">
              {featuredQueries.map((item) => (
                <button
                  key={item}
                  type="button"
                  className="tagButton"
                  onClick={() =>
                    setDraft((current) => ({
                      ...current,
                      query: current.query.includes(item) ? current.query : `${current.query} ${item}`.trim(),
                    }))
                  }
                >
                  {item}
                </button>
              ))}
            </div>

            <div className="inlineRunRow">
              <input
                value={replayRunId}
                onChange={(event) => setReplayRunId(event.target.value)}
                placeholder="输入 Run ID 回放协作记录"
              />
              <button
                type="button"
                className="secondaryButton"
                onClick={handleLoadRun}
                disabled={replayLoading}
              >
                {replayLoading ? "加载中..." : "回放 Run"}
              </button>
            </div>

            <div className="resultCard">
              <h3>最近任务</h3>
              <ul className="simpleList">
                {recentTasks.length ? (
                  recentTasks.map((item) => (
                    <li key={item.id}>
                      {item.title} · {item.status} · {item.completed_steps}/{item.total_steps}
                    </li>
                  ))
                ) : (
                  <li>当前暂无可展示任务。</li>
                )}
              </ul>
            </div>

            <div className="resultCard">
              <h3>最近案例</h3>
              <ul className="simpleList">
                {recentCases.length ? (
                  recentCases.map((item) => (
                    <li key={item.id}>
                      {item.title} · {item.status} · {item.equipment_model || item.equipment_type}
                    </li>
                  ))
                ) : (
                  <li>当前暂无可展示案例。</li>
                )}
              </ul>
            </div>
          </div>
        </SectionCard>
      </div>

      {error ? <p className="errorText">{error}</p> : null}

      {result ? (
        <div className="panelStack">
          <SectionCard
            title="协作结论与执行决策"
            description="这里汇总本次工单上下文、Agent 协作摘要和是否可以进入现场执行。"
          >
            <div className="panelStack">
              <div className="selectionSummary">
                <div className="infoStrip">
                  <span>Run ID：</span>
                  {result.run_id}
                </div>
                <span className={`statusBadge ${getExecutionTone(result.execution_brief?.status)}`}>
                  {EXECUTION_STATUS_LABELS[result.execution_brief?.status || "need_more_input"] || "待补充信息"}
                </span>
              </div>

              <p>{result.summary}</p>

              <div className="buttonRow">
                <button type="button" onClick={handleCreateTask} disabled={creatingTask}>
                  {creatingTask ? "创建中..." : "创建正式任务并进入执行"}
                </button>
              </div>

              <div className="detailGrid">
                <article className="resultCard">
                  <h3>工单摘要</h3>
                  <ul className="simpleList">
                    <li>工单编号：{result.request_context?.work_order_id || "未填写"}</li>
                    <li>设备编号：{result.request_context?.asset_code || "未填写"}</li>
                    <li>报修来源：{result.request_context?.report_source || "未填写"}</li>
                    <li>
                      优先级 / 模式：
                      {PRIORITY_LABELS[(result.request_context?.priority as PriorityLevel) || "medium"]} /{" "}
                      {MAINTENANCE_LABELS[
                        (result.request_context?.maintenance_level as MaintenanceLevel) || "standard"
                      ]}
                    </li>
                    <li>
                      设备对象：
                      {result.request_context?.equipment_model || result.request_context?.equipment_type || "待补充"}
                    </li>
                    <li>故障类型：{result.request_context?.fault_type || "待补充"}</li>
                    <li>现场图片：{result.request_context?.has_image ? "已上传" : "未上传"}</li>
                  </ul>
                </article>

                <article className="resultCard">
                  <h3>执行决策</h3>
                  <p>{result.execution_brief?.decision || "待补充执行决策。"}</p>
                  <ul className="simpleList">
                    <li>推荐流程：{result.execution_brief?.recommended_path || "待生成"}</li>
                    <li>有效查询：{result.effective_query || "无"}</li>
                    <li>
                      有效检索词：
                      {result.effective_keywords.length ? result.effective_keywords.join(" / ") : "无"}
                    </li>
                  </ul>
                  {result.image_analysis ? (
                    <p className="muted">
                      图片分析：
                      {result.image_analysis.source === "vision_model" ? "视觉模型" : "回退模式"} ·{" "}
                      {result.image_analysis.summary}
                    </p>
                  ) : null}
                </article>
              </div>
            </div>
          </SectionCard>

          <SectionCard
            title="知识依据锁定"
            description="可以先看 Agent 自动选中的知识依据，再手动调整勾选范围，刷新步骤预案。"
          >
            <div className="panelStack">
              <div className="selectionSummary">
                <div className="infoStrip">
                  <span>已锁定依据：</span>
                  {selectedChunkIds.length} / {result.knowledge_results.length}
                </div>
                <div className="tagRow">
                  {(result.effective_keywords || []).map((item) => (
                    <span key={item} className="tag">
                      {item}
                    </span>
                  ))}
                </div>
              </div>

              {result.image_analysis ? (
                <article className="resultCard">
                  <h3>图片识别线索</h3>
                  <p className="muted">
                    {result.image_analysis.source === "vision_model" ? "视觉模型" : "回退模式"} ·{" "}
                    {result.image_analysis.keywords.join(" / ") || "无关键词"}
                  </p>
                  <p className="excerpt">{result.image_analysis.summary}</p>
                  {result.image_analysis.warning ? (
                    <p className="errorText">{result.image_analysis.warning}</p>
                  ) : null}
                </article>
              ) : null}

              {result.knowledge_results.length ? (
                result.knowledge_results.map((item) => (
                  <article key={item.chunk_id} className="resultCard">
                    <div className="cardTitleRow">
                      <div className="resultMeta">
                        <h3>{item.title}</h3>
                        <p>
                          {item.source_name} · {item.page_reference ?? "页码待补充"} ·{" "}
                          {item.section_reference ?? "章节待补充"}
                        </p>
                      </div>
                      <label className="toggleRow">
                        <input
                          type="checkbox"
                          checked={selectedChunkIds.includes(item.chunk_id)}
                          onChange={() => toggleSelectedChunk(item.chunk_id)}
                        />
                        纳入作业依据
                      </label>
                    </div>
                    <p className="excerpt">{item.excerpt}</p>
                    <p className="reason">{item.recommendation_reason}</p>
                  </article>
                ))
              ) : (
                <p className="muted">当前条件下暂无稳定知识命中，请补充设备信息或图片后重新触发协作。</p>
              )}
            </div>
          </SectionCard>

          <div className="twoGrid">
            <SectionCard
              title="标准化步骤预案"
              description="WorkOrderPlannerAgent 会把已锁定知识转换成可执行的标准化检修步骤。"
            >
              <div className="stackList">
                {result.task_plan_preview.length ? (
                  result.task_plan_preview.map((step) => (
                    <article key={`${step.step_order}-${step.title}`} className="stepCard">
                      <p className="eyebrow">STEP {step.step_order}</p>
                      <h3>{step.title}</h3>
                      <p>{step.instruction}</p>
                      {step.risk_warning ? <p className="errorText">风险：{step.risk_warning}</p> : null}
                      {step.caution ? <p className="muted">注意：{step.caution}</p> : null}
                      {step.confirmation_text ? <p className="muted">确认：{step.confirmation_text}</p> : null}
                    </article>
                  ))
                ) : (
                  <p className="muted">当前尚未生成步骤预案。</p>
                )}
              </div>
            </SectionCard>

            <SectionCard
              title="风险控制与下一步"
              description="RiskControlAgent 会输出现场风险、缺项提醒以及当前工单的执行建议。"
            >
              <div className="panelStack">
                <article className="resultCard">
                  <h3>执行建议</h3>
                  <p>{result.execution_brief?.decision || "待生成执行建议。"}</p>
                  <ul className="simpleList">
                    {(result.execution_brief?.next_actions || []).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </article>

                <article className="resultCard">
                  <h3>风险提示</h3>
                  <ul className="simpleList">
                    {result.risk_findings.length ? (
                      result.risk_findings.map((item) => <li key={item}>{item}</li>)
                    ) : (
                      <li>当前未识别到额外风险提醒。</li>
                    )}
                  </ul>
                </article>
              </div>
            </SectionCard>
          </div>

          <div className="twoGrid">
            <SectionCard
              title="相似案例与沉淀建议"
              description="CaseCuratorAgent 会推荐最近可参考案例，并提示本次工单如何沉淀为可复用知识。"
            >
              <div className="panelStack">
                {result.related_cases.length ? (
                  result.related_cases.map((item) => (
                    <article key={item.id} className="resultCard">
                      <div className="resultMeta">
                        <h3>{item.title}</h3>
                        <p>
                          {item.equipment_model || item.equipment_type} · {item.status} · {formatDate(item.updated_at)}
                        </p>
                      </div>
                      <p className="muted">{item.match_reason}</p>
                    </article>
                  ))
                ) : (
                  <p className="muted">当前暂无可直接参考的相似案例。</p>
                )}

                <article className="resultCard">
                  <h3>沉淀建议</h3>
                  <ul className="simpleList">
                    {result.case_suggestions.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </article>
              </div>
            </SectionCard>

            <SectionCard
              title="Agent 协作时间线"
              description="这里用于答辩时展示“多智能体协作完成整条检修链路”，而不是单次模型输出。"
            >
              <div className="agentGrid">
                {result.agents.map((agent) => {
                  const uniqueCitations = Array.from(
                    new Set(agent.citations.map((citation) => citation.trim()).filter(Boolean)),
                  );

                  return (
                    <article key={agent.agent_name} className="resultCard">
                      <h3>{agent.title}</h3>
                      <p className="muted">{agent.agent_name}</p>
                      <p>{agent.summary}</p>
                      {uniqueCitations.length ? (
                        <ul className="bulletList">
                          {uniqueCitations.map((citation) => (
                            <li key={citation}>{citation}</li>
                          ))}
                        </ul>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            </SectionCard>
          </div>
        </div>
      ) : (
        <SectionCard
          title="等待协作触发"
          description="录入工单后点击“触发多 Agent 协作”，页面会自动生成知识依据、步骤预案、风险控制和案例建议。"
        >
          <p className="muted">
            当前推荐先使用左侧预设场景完成演示，再根据现场输入调整工单编号、型号、优先级和故障图片。
          </p>
        </SectionCard>
      )}
    </div>
  );
}
