type KnowledgeAnchorLike = {
  page_reference?: string | null;
  section_reference?: string | null;
  section_path?: string | null;
  step_anchor?: string | null;
  image_anchor?: string | null;
};

export function formatKnowledgeAnchor(item: KnowledgeAnchorLike): string {
  const parts = [
    item.page_reference?.trim(),
    item.section_path?.trim(),
    item.section_reference?.trim(),
    item.step_anchor?.trim(),
    item.image_anchor?.trim(),
  ].filter((value, index, array) => Boolean(value) && array.indexOf(value) === index);
  return parts.length ? parts.join(" · ") : "锚点待补充";
}

export function buildKnowledgeTraceHref(params: {
  documentId: number;
  chunkId?: number | null;
  sourceType?: string | null;
}): string {
  const search = new URLSearchParams();
  search.set("documentId", String(params.documentId));
  if (typeof params.chunkId === "number" && params.chunkId > 0) {
    search.set("chunkId", String(params.chunkId));
  }
  if (params.sourceType?.trim()) {
    search.set("sourceType", params.sourceType.trim());
  }
  return `/knowledge?${search.toString()}`;
}
