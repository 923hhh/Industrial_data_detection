import type { PropsWithChildren } from "react";

type SectionCardProps = PropsWithChildren<{
  title: string;
  description?: string;
}>;

export function SectionCard({ title, description, children }: SectionCardProps) {
  return (
    <section className="sectionCard">
      <div className="sectionHeader">
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      {children}
    </section>
  );
}

