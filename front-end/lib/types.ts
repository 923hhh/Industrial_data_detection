export type WorkbenchStatCard = {
  key: string;
  label: string;
  value: number;
  accent: string;
};

export type WorkbenchTaskSummary = {
  id: number;
  title: string;
  equipment_type: string;
  equipment_model?: string | null;
  maintenance_level: string;
  status: string;
  total_steps: number;
  completed_steps: number;
  updated_at?: string | null;
};

export type WorkbenchCaseSummary = {
  id: number;
  title: string;
  equipment_type: string;
  equipment_model?: string | null;
  status: string;
  task_id?: number | null;
  updated_at?: string | null;
};

export type WorkbenchOverviewResponse = {
  generated_at: string;
  stats: WorkbenchStatCard[];
  featured_queries: string[];
  agent_capabilities: string[];
  recent_tasks: WorkbenchTaskSummary[];
  recent_cases: WorkbenchCaseSummary[];
};

export type KnowledgeSearchHit = {
  chunk_id: number;
  document_id: number;
  title: string;
  source_name: string;
  source_type: string;
  equipment_type: string;
  equipment_model?: string | null;
  fault_type?: string | null;
  excerpt: string;
  section_reference?: string | null;
  page_reference?: string | null;
  recommendation_reason: string;
  score?: number | null;
};

export type KnowledgeImageAnalysis = {
  summary: string;
  keywords: string[];
  source: string;
  warning?: string | null;
};

export type KnowledgeSearchResponse = {
  query?: string | null;
  effective_query?: string | null;
  effective_keywords: string[];
  image_analysis?: KnowledgeImageAnalysis | null;
  total: number;
  results: KnowledgeSearchHit[];
};

export type KnowledgeImportJobResponse = {
  id: number;
  import_type: string;
  title?: string | null;
  source_name: string;
  source_type: string;
  equipment_type: string;
  equipment_model?: string | null;
  fault_type?: string | null;
  section_reference?: string | null;
  replace_existing: boolean;
  status: string;
  page_count?: number | null;
  chunk_count?: number | null;
  document_id?: number | null;
  preview_excerpt?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

export type KnowledgeDocumentListItem = {
  id: number;
  title: string;
  source_name: string;
  source_type: string;
  equipment_type: string;
  equipment_model?: string | null;
  fault_type?: string | null;
  status: string;
  chunk_count: number;
  created_at: string;
  updated_at: string;
};

export type KnowledgeDocumentListResponse = {
  total: number;
  documents: KnowledgeDocumentListItem[];
};

export type KnowledgeChunkPreview = {
  chunk_id: number;
  chunk_index: number;
  heading?: string | null;
  content: string;
  page_reference?: string | null;
  section_reference?: string | null;
};

export type KnowledgeChunkPreviewResponse = {
  document_id: number;
  total: number;
  chunks: KnowledgeChunkPreview[];
};

export type AgentTaskPreviewStep = {
  step_order: number;
  title: string;
  instruction: string;
  risk_warning?: string | null;
  caution?: string | null;
  confirmation_text?: string | null;
};

export type AgentRunStep = {
  agent_name: string;
  title: string;
  status: string;
  summary: string;
  citations: string[];
};

export type AgentAssistResponse = {
  run_id: string;
  status: string;
  summary: string;
  effective_query?: string | null;
  effective_keywords: string[];
  image_analysis?: KnowledgeImageAnalysis | null;
  knowledge_results: KnowledgeSearchHit[];
  task_plan_preview: AgentTaskPreviewStep[];
  risk_findings: string[];
  case_suggestions: string[];
  agents: AgentRunStep[];
  created_at: string;
};

export type MaintenanceCaseSummary = {
  id: number;
  title: string;
  equipment_type: string;
  equipment_model?: string | null;
  fault_type?: string | null;
  status: string;
  task_id?: number | null;
  source_document_id?: number | null;
  updated_at?: string | null;
};

export type MaintenanceCaseListResponse = {
  total: number;
  cases: MaintenanceCaseSummary[];
};

export type MaintenanceTaskHistoryResponse = {
  total: number;
  tasks: WorkbenchTaskSummary[];
};
