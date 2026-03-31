import { notFound } from "next/navigation";

import { CaseReviewPanel } from "@/components/case-review-panel";
import { getMaintenanceCase } from "@/lib/api";

type CaseDetailPageProps = {
  params: Promise<{
    caseId: string;
  }>;
};

export default async function CaseDetailPage({ params }: CaseDetailPageProps) {
  const { caseId } = await params;
  const numericCaseId = Number(caseId);

  if (!Number.isFinite(numericCaseId) || numericCaseId <= 0) {
    notFound();
  }

  let caseDetail;
  try {
    caseDetail = await getMaintenanceCase(numericCaseId);
  } catch {
    notFound();
  }

  return (
    <div className="page">
      <section className="hero">
        <p className="eyebrow">Case Review</p>
        <h2>案例详情与审核页</h2>
        <p>这里用于查看案例沉淀结果、补充人工修正，并执行审核入库或驳回。</p>
      </section>

      <CaseReviewPanel initialCase={caseDetail} />
    </div>
  );
}
