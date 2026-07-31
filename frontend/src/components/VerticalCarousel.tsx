import { useEffect, useRef, useState } from "react";

export interface VerticalCarouselItem {
  id: string;
  label: string;
  sublabel?: string;
  icon?: string;
  active?: boolean;
  onSelect?: () => void;
}

interface VerticalCarouselProps {
  title: string;
  items: VerticalCarouselItem[];
  /** Cuántos elementos son visibles a la vez dentro del carrusel */
  visibleCount?: number;
  autoPlayMs?: number;
  emptyMessage?: string;
}

/**
 * Carrusel vertical: hace scroll de un panel de N items visibles, desplazando
 * de a un item por vez (arriba/abajo), con auto-rotación pausable al pasar
 * el mouse. Pensado para paneles laterales (categorías, ofertas destacadas)
 * donde el eje natural de la lista es vertical, no horizontal.
 */
export function VerticalCarousel({
  title,
  items,
  visibleCount = 5,
  autoPlayMs = 4000,
  emptyMessage = "No hay elementos disponibles.",
}: VerticalCarouselProps) {
  const [startIndex, setStartIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const maxStart = Math.max(items.length - visibleCount, 0);

  useEffect(() => {
    if (paused || maxStart === 0) return;
    timerRef.current = setInterval(() => {
      setStartIndex((i) => (i >= maxStart ? 0 : i + 1));
    }, autoPlayMs);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [paused, maxStart, autoPlayMs]);

  const step = (dir: 1 | -1) => {
    setStartIndex((i) => {
      const next = i + dir;
      if (next < 0) return maxStart;
      if (next > maxStart) return 0;
      return next;
    });
  };

  if (items.length === 0) {
    return (
      <section className="w-full">
        <h2 className="font-display text-lg font-bold text-ink mb-3">{title}</h2>
        <p className="text-slate-500 text-sm">{emptyMessage}</p>
      </section>
    );
  }

  const visible = items.slice(startIndex, startIndex + visibleCount);

  return (
    <section
      className="w-full bg-white border border-slate-200 rounded-lg p-4"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      aria-label={title}
    >
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-display text-lg font-bold text-ink">{title}</h2>
        {items.length > visibleCount && (
          <div className="flex gap-1.5">
            <button
              type="button"
              aria-label="Elemento anterior"
              onClick={() => step(-1)}
              className="w-7 h-7 rounded-full border border-slate-300 flex items-center justify-center text-xs hover:bg-slate-100 transition-colors"
            >
              ˄
            </button>
            <button
              type="button"
              aria-label="Elemento siguiente"
              onClick={() => step(1)}
              className="w-7 h-7 rounded-full border border-slate-300 flex items-center justify-center text-xs hover:bg-slate-100 transition-colors"
            >
              ˅
            </button>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-1 transition-all duration-300">
        {visible.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={item.onSelect}
            className={`w-full text-left px-3 py-2.5 rounded-md flex items-center gap-2 text-sm transition-colors ${
              item.active
                ? "bg-brand-50 text-brand-700 font-semibold"
                : "text-ink hover:bg-slate-50"
            }`}
          >
            {item.icon && <span aria-hidden="true">{item.icon}</span>}
            <span className="flex-1 truncate">{item.label}</span>
            {item.sublabel && (
              <span className="text-xs text-slate-400 shrink-0">{item.sublabel}</span>
            )}
          </button>
        ))}
      </div>

      {items.length > visibleCount && (
        <div className="flex justify-center gap-1.5 mt-3">
          {Array.from({ length: maxStart + 1 }).map((_, i) => (
            <button
              key={i}
              aria-label={`Ir a la posición ${i + 1}`}
              onClick={() => setStartIndex(i)}
              className={`h-1.5 rounded-full transition-all ${
                i === startIndex ? "w-5 bg-brand-600" : "w-1.5 bg-slate-300 hover:bg-slate-400"
              }`}
            />
          ))}
        </div>
      )}
    </section>
  );
}
