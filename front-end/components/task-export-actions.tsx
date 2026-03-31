"use client";

import Link from "next/link";

type TaskExportActionsProps = {
  taskId: number;
};

export function TaskExportActions({ taskId }: TaskExportActionsProps) {
  return (
    <div className="buttonRow printHidden">
      <button type="button" onClick={() => window.print()}>
        打印作业单
      </button>
      <Link href={`/tasks/${taskId}`} className="inlineActionLink">
        返回任务详情
      </Link>
      <Link href={`/cases/new?taskId=${taskId}`} className="inlineActionLink">
        继续沉淀案例
      </Link>
    </div>
  );
}
