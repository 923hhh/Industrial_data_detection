import type {
  AgentAssistResponse,
  KnowledgeChunkPreviewResponse,
  KnowledgeDocumentDetailResponse,
  KnowledgeDocumentListResponse,
  KnowledgeImportJobListResponse,
  KnowledgeImportPreviewResponse,
  KnowledgeImportJobResponse,
  KnowledgeSearchResponse,
  MaintenanceCaseListResponse,
  MaintenanceCaseResponse,
  MaintenanceTaskExportResponse,
  MaintenanceTaskResponse,
  MaintenanceTaskHistoryResponse,
  WorkbenchOverviewResponse,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

async function parseJson<T>(response: Response): Promise<T> {
  const rawText = await response.text();
  if (!response.ok) {
    let message = rawText || `Request failed with status ${response.status}`;

    if (rawText) {
      try {
        const payload = JSON.parse(rawText) as {
          message?: string;
          error_code?: string;
          request_id?: string;
        };
        if (payload.message) {
          message = payload.message;
          if (payload.error_code) {
            message += ` [${payload.error_code}]`;
          }
          if (payload.request_id) {
            message += ` (request: ${payload.request_id})`;
          }
        }
      } catch {
        // Fall back to raw text when the response body is not JSON.
      }
    }

    throw new Error(message);
  }
  return JSON.parse(rawText) as T;
}

export async function getWorkbenchOverview(): Promise<WorkbenchOverviewResponse | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/workbench/overview`, {
      cache: "no-store",
    });
    return await parseJson<WorkbenchOverviewResponse>(response);
  } catch {
    return null;
  }
}

export async function getTaskHistory(params?: {
  limit?: number;
  status?: string;
  priority?: string;
  work_order_id?: string;
}): Promise<MaintenanceTaskHistoryResponse | null> {
  try {
    const search = new URLSearchParams();
    search.set("limit", String(params?.limit ?? 10));
    if (params?.status?.trim()) search.set("status", params.status.trim());
    if (params?.priority?.trim()) search.set("priority", params.priority.trim());
    if (params?.work_order_id?.trim()) search.set("work_order_id", params.work_order_id.trim());

    const response = await fetch(`${API_BASE_URL}/api/v1/history?${search.toString()}`, {
      cache: "no-store",
    });
    return await parseJson<MaintenanceTaskHistoryResponse>(response);
  } catch {
    return null;
  }
}

export async function createMaintenanceTask(
  payload: Record<string, unknown>,
): Promise<MaintenanceTaskResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/tasks`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return parseJson<MaintenanceTaskResponse>(response);
}

export async function getMaintenanceTask(taskId: number): Promise<MaintenanceTaskResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}`, {
    cache: "no-store",
  });
  return parseJson<MaintenanceTaskResponse>(response);
}

export async function updateMaintenanceTaskStep(
  taskId: number,
  stepId: number,
  payload: Record<string, unknown>,
): Promise<MaintenanceTaskResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}/steps/${stepId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return parseJson<MaintenanceTaskResponse>(response);
}

export async function getMaintenanceTaskExport(taskId: number): Promise<MaintenanceTaskExportResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/export/${taskId}`, {
    cache: "no-store",
  });
  return parseJson<MaintenanceTaskExportResponse>(response);
}

export async function getCases(params?: {
  limit?: number;
  status?: string;
  priority?: string;
  work_order_id?: string;
}): Promise<MaintenanceCaseListResponse | null> {
  try {
    const search = new URLSearchParams();
    search.set("limit", String(params?.limit ?? 10));
    if (params?.status?.trim()) search.set("status", params.status.trim());
    if (params?.priority?.trim()) search.set("priority", params.priority.trim());
    if (params?.work_order_id?.trim()) search.set("work_order_id", params.work_order_id.trim());

    const response = await fetch(`${API_BASE_URL}/api/v1/cases?${search.toString()}`, {
      cache: "no-store",
    });
    return await parseJson<MaintenanceCaseListResponse>(response);
  } catch {
    return null;
  }
}

export async function createMaintenanceCase(
  payload: Record<string, unknown>,
): Promise<MaintenanceCaseResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/cases`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return parseJson<MaintenanceCaseResponse>(response);
}

export async function getMaintenanceCase(caseId: number): Promise<MaintenanceCaseResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/cases/${caseId}`, {
    cache: "no-store",
  });
  return parseJson<MaintenanceCaseResponse>(response);
}

export async function addMaintenanceCaseCorrection(
  caseId: number,
  payload: Record<string, unknown>,
): Promise<MaintenanceCaseResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/cases/${caseId}/corrections`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return parseJson<MaintenanceCaseResponse>(response);
}

export async function reviewMaintenanceCase(
  caseId: number,
  payload: Record<string, unknown>,
): Promise<MaintenanceCaseResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/cases/${caseId}/review`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return parseJson<MaintenanceCaseResponse>(response);
}

export async function searchKnowledge(payload: Record<string, unknown>): Promise<KnowledgeSearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return parseJson<KnowledgeSearchResponse>(response);
}

export async function importKnowledgePdf(formData: FormData): Promise<KnowledgeImportJobResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/imports`, {
    method: "POST",
    body: formData,
  });
  return parseJson<KnowledgeImportJobResponse>(response);
}

export async function previewKnowledgeImport(
  formData: FormData,
): Promise<KnowledgeImportPreviewResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/imports/preview`, {
    method: "POST",
    body: formData,
  });
  return parseJson<KnowledgeImportPreviewResponse>(response);
}

export async function getKnowledgeImportJob(jobId: number): Promise<KnowledgeImportJobResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/imports/${jobId}`, {
    cache: "no-store",
  });
  return parseJson<KnowledgeImportJobResponse>(response);
}

export async function getKnowledgeImportJobs(limit = 8): Promise<KnowledgeImportJobListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/imports?limit=${limit}`, {
    cache: "no-store",
  });
  return parseJson<KnowledgeImportJobListResponse>(response);
}

export async function getKnowledgeDocuments(params?: {
  limit?: number;
  query?: string;
  equipment_type?: string;
  equipment_model?: string;
  source_type?: string;
}): Promise<KnowledgeDocumentListResponse> {
  const search = new URLSearchParams();
  search.set("limit", String(params?.limit ?? 12));
  if (params?.query?.trim()) search.set("query", params.query.trim());
  if (params?.equipment_type?.trim()) search.set("equipment_type", params.equipment_type.trim());
  if (params?.equipment_model?.trim()) search.set("equipment_model", params.equipment_model.trim());
  if (params?.source_type?.trim()) search.set("source_type", params.source_type.trim());

  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/documents?${search.toString()}`, {
    cache: "no-store",
  });
  return parseJson<KnowledgeDocumentListResponse>(response);
}

export async function getKnowledgeDocumentDetail(
  documentId: number,
): Promise<KnowledgeDocumentDetailResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/documents/${documentId}`, {
    cache: "no-store",
  });
  return parseJson<KnowledgeDocumentDetailResponse>(response);
}

export async function getKnowledgeDocumentChunks(
  documentId: number,
  limit = 6,
): Promise<KnowledgeChunkPreviewResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/knowledge/documents/${documentId}/chunks?limit=${limit}`,
    {
      cache: "no-store",
    },
  );
  return parseJson<KnowledgeChunkPreviewResponse>(response);
}

export async function assistWithAgents(payload: Record<string, unknown>): Promise<AgentAssistResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/agents/assist`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return parseJson<AgentAssistResponse>(response);
}

export async function getAgentRun(runId: string): Promise<AgentAssistResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/agents/runs/${runId}`, {
    cache: "no-store",
  });
  return parseJson<AgentAssistResponse>(response);
}

export { API_BASE_URL };
