export default function PriceBadge({ estimate, demo }: { estimate: boolean; demo?: boolean }) {
  if (demo) return <span className="rounded-md bg-sand-100 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-sand-600">sample</span>;
  return estimate ? (
    <span className="rounded-md bg-paper px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-muted ring-1 ring-line">estimate</span>
  ) : (
    <span className="rounded-md bg-sea-50 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-sea-700">live</span>
  );
}
