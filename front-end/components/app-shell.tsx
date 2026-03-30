import Link from "next/link";
import type { PropsWithChildren } from "react";

const NAV_ITEMS = [
  { href: "/", label: "工作台" },
  { href: "/knowledge", label: "知识检索" },
  { href: "/tasks", label: "检修任务" },
  { href: "/cases", label: "案例沉淀" },
  { href: "/history", label: "历史记录" },
  { href: "/agents", label: "Agent 协作" },
];

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <p className="eyebrow">SoftBei Workbench</p>
          <h1>设备检修知识与作业助手</h1>
          <p className="muted">
            正式前端骨架，面向知识检索、标准化作业、案例沉淀和 Agent 协作展示。
          </p>
        </div>
        <nav className="nav">
          {NAV_ITEMS.map((item) => (
            <Link key={item.href} href={item.href} className="navLink">
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="sidebarCard">
          <h3>当前主线</h3>
          <p>知识检索 → Agent 协作 → 作业指引 → 步骤执行 → 案例沉淀 → 审核回流</p>
        </div>
      </aside>
      <main className="mainContent">{children}</main>
    </div>
  );
}

