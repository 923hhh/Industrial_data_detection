type StatCardProps = {
  label: string;
  value: number;
  accent?: string;
};

export function StatCard({ label, value, accent = "neutral" }: StatCardProps) {
  return (
    <article className={`statCard accent-${accent}`}>
      <p className="statLabel">{label}</p>
      <p className="statValue">{value}</p>
    </article>
  );
}

