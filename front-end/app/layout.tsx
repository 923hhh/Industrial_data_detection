import type { Metadata } from "next";
import type { PropsWithChildren } from "react";

import { AppShell } from "@/components/app-shell";

import "./globals.css";

export const metadata: Metadata = {
  title: "设备检修知识与作业助手",
  description: "软件杯正式前端工作台骨架",
};

export default function RootLayout({ children }: PropsWithChildren) {
  return (
    <html lang="zh-CN">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}

