import Link from "next/link";

import { SectionCard } from "@/components/section-card";
import { getTaskHistory } from "@/lib/api";

export default async function TasksPage() {
  const payload = await getTaskHistory(10);

  return (
    <div className="page">
      <section className="hero">
        <p className="eyebrow">Task Center</p>
        <h2>检修任务中心</h2>
        <p>这里承接由知识引用驱动的标准化检修任务、步骤状态和导出结果。</p>
      </section>

      <SectionCard
        title="最近任务"
        description="当前任务中心已支持进入详情执行页，后续会继续补工单信息、案例沉淀联动和正式导出。"
      >
        <div className="tableCard">
          <table>
            <thead>
              <tr>
                <th>任务标题</th>
                <th>状态</th>
                <th>设备</th>
                <th>进度</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {(payload?.tasks ?? []).map((task) => (
                <tr key={task.id}>
                  <td>{task.title}</td>
                  <td>{task.status}</td>
                  <td>{task.equipment_model || task.equipment_type}</td>
                  <td>
                    {task.completed_steps}/{task.total_steps}
                  </td>
                  <td>
                    <Link href={`/tasks/${task.id}`} className="inlineActionLink">
                      进入执行
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  );
}
