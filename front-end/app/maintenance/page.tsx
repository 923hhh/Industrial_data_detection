"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { maintenanceApiBase } from "@/lib/api";

/**
 * 检修域 MVP 联调探针：无鉴权 health + 说明。
 * 完整 Bearer 调用请使用 `@/lib/maintenance-client`（`maintenanceLogin` / `createMaintenanceClient`）。
 */
export default function MaintenanceProbePage() {
  const [health, setHealth] = useState<unknown>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${maintenanceApiBase}/health`, { cache: "no-store" })
      .then((r) => r.json())
      .then(setHealth)
      .catch((e: Error) => setErr(e.message));
  }, []);

  return (
    <div className="page" style={{ maxWidth: 720, margin: "2rem auto", padding: "0 1rem" }}>
      <p className="eyebrow">检修域 MVP</p>
      <h2>联调探针</h2>
      <p>
        基址：<code>{maintenanceApiBase}</code>。登录与带 Token 请求封装见{" "}
        <code>lib/maintenance-client.ts</code>。
      </p>
      <p>
        <Link href="/">返回首页</Link>
      </p>
      <h3>GET /health</h3>
      {err ? <pre style={{ color: "salmon" }}>{err}</pre> : <pre>{JSON.stringify(health, null, 2)}</pre>}
    </div>
  );
}
