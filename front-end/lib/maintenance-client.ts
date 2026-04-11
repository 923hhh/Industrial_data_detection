/**
 * 检修域 MVP（`/api/v1/maintenance`）封装：登录、Bearer 请求、统一解析 success / business_code。
 * 基址与 `api.ts` 中 `maintenanceApiBase` 一致。
 */
import { maintenanceApiBase } from "@/lib/api";

export type MaintenanceSuccessEnvelope<T> = {
  success: true;
  data: T;
  business_code: string | null;
  message: string | null;
};

export type MaintenanceErrorEnvelope = {
  success: false;
  data: unknown;
  business_code: string;
  message: string;
  errors?: unknown;
};

export type MaintenanceEnvelope<T> = MaintenanceSuccessEnvelope<T> | MaintenanceErrorEnvelope;

export class MaintenanceBizError extends Error {
  readonly businessCode: string;
  readonly payload: unknown;
  readonly httpStatus: number;

  constructor(httpStatus: number, businessCode: string, message: string, payload: unknown) {
    super(message || businessCode);
    this.name = "MaintenanceBizError";
    this.httpStatus = httpStatus;
    this.businessCode = businessCode;
    this.payload = payload;
  }
}

export type MaintenanceLoginData = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: { id: number; username: string; roles: string[] };
};

export type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

/** 登录并返回 data（含 access_token）。HTTP 4xx/5xx 或 success=false 时抛 MaintenanceBizError。 */
export async function maintenanceLogin(username: string, password: string): Promise<MaintenanceLoginData> {
  const r = await fetch(`${maintenanceApiBase}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const body = (await r.json()) as MaintenanceEnvelope<MaintenanceLoginData>;
  if (!r.ok || !body.success) {
    const b = body as MaintenanceErrorEnvelope;
    throw new MaintenanceBizError(r.status, b.business_code ?? "HTTP_ERROR", b.message ?? r.statusText, b.data);
  }
  return body.data;
}

export type MaintenanceClient = {
  /** 原始封装：path 以 `/` 开头，如 `/devices?page=1&page_size=20` */
  mvpFetchJson<T>(path: string, init?: RequestInit): Promise<T>;
  getDevices(page?: number, pageSize?: number): Promise<Paginated<Record<string, unknown>>>;
  listAuditLogs(page?: number, pageSize?: number): Promise<Paginated<Record<string, unknown>>>;
};

/**
 * 带 Bearer 的检修域客户端。业务错误（HTTP 200 但 success=false）抛 MaintenanceBizError。
 */
export function createMaintenanceClient(accessToken: string): MaintenanceClient {
  const authHeaders = (): HeadersInit => ({
    Authorization: `Bearer ${accessToken}`,
  });

  async function mvpFetchJson<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    if (!headers.has("Authorization")) {
      const a = authHeaders() as Record<string, string>;
      headers.set("Authorization", a.Authorization!);
    }
    if (init.body != null && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    const r = await fetch(`${maintenanceApiBase}${path}`, { ...init, headers });
    const body = (await r.json()) as MaintenanceEnvelope<T>;
    if (!body.success) {
      const b = body as MaintenanceErrorEnvelope;
      throw new MaintenanceBizError(r.status, b.business_code, b.message, b.data);
    }
    if (!r.ok) {
      throw new MaintenanceBizError(r.status, "HTTP_ERROR", r.statusText, body);
    }
    return body.data;
  }

  return {
    mvpFetchJson,
    getDevices(page = 1, pageSize = 20) {
      return mvpFetchJson<Paginated<Record<string, unknown>>>(
        `/devices?page=${page}&page_size=${pageSize}`,
      );
    },
    listAuditLogs(page = 1, pageSize = 20) {
      return mvpFetchJson<Paginated<Record<string, unknown>>>(
        `/admin/audit-logs?page=${page}&page_size=${pageSize}`,
      );
    },
  };
}
