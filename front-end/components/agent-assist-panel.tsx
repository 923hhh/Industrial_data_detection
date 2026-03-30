"use client";

import { useState } from "react";

import { assistWithAgents } from "@/lib/api";
import type { AgentAssistResponse } from "@/lib/types";

export function AgentAssistPanel() {
  const [query, setQuery] = useState("发动机冷启动困难，伴随火花塞积碳");
  const [equipmentType, setEquipmentType] = useState("摩托车发动机");
  const [equipmentModel, setEquipmentModel] = useState("LX200");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AgentAssistResponse | null>(null);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const payload = await assistWithAgents({
        query,
        equipment_type: equipmentType,
        equipment_model: equipmentModel || null,
        maintenance_level: "standard",
      });
      setResult(payload);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Agent 协作失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panelStack">
      <div className="formGrid">
        <label>
          <span>故障描述</span>
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
        <button onClick={handleRun} disabled={loading}>
          {loading ? "协作中..." : "运行 Agent 协作"}
        </button>
      </div>
      {error ? <p className="errorText">{error}</p> : null}
      {result ? (
        <div className="panelStack">
          <div className="infoStrip">
            <span>Run ID：</span>
            {result.run_id}
          </div>
          <p>{result.summary}</p>
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
        </div>
      ) : null}
    </div>
  );
}
