export function StarRating({ value, count }: { value: number; count?: number }) {
  const rounded = Math.round(value);
  return (
    <div className="flex items-center gap-1 text-xs">
      <span className="text-star">
        {"★".repeat(Math.max(0, Math.min(5, rounded)))}
        {"☆".repeat(5 - Math.max(0, Math.min(5, rounded)))}
      </span>
      <span className="text-slate-500">
        {value.toFixed(1)}
        {typeof count === "number" && ` (${count})`}
      </span>
    </div>
  );
}
