import type {
  AgentAssistResponse,
  KnowledgeChunkPreviewResponse,
  KnowledgeDocumentListResponse,
  KnowledgeImportJobListResponse,
  KnowledgeImportPreviewResponse,
  KnowledgeImportJobResponse,
  KnowledgeSearchResponse,
  MaintenanceCaseListResponse,
  MaintenanceTaskHistoryResponse,
  WorkbenchOverviewResponse,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
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

export async function getTaskHistory(limit = 10): Promise<MaintenanceTaskHistoryResponse | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/history?limit=${limit}`, {
      cache: "no-store",
    });
    return await parseJson<MaintenanceTaskHistoryResponse>(response);
  } catch {
    return null;
  }
}

export async function getCases(limit = 10): Promise<MaintenanceCaseListResponse | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/cases?limit=${limit}`, {
      cache: "no-store",
    });
    return await parseJson<MaintenanceCaseListResponse>(response);
  } catch {
    return null;
  }
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

export async function getKnowledgeDocuments(limit = 12): Promise<KnowledgeDocumentListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/documents?limit=${limit}`, {
    cache: "no-store",
  });
  return parseJson<KnowledgeDocumentListResponse>(response);
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

export { API_BASE_URL };
