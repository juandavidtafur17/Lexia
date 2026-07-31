import { useEffect, useRef, useState, type ReactNode } from "react";

interface HorizontalCarouselProps {
  /** Título de la sección (ej. "Más vendidos") */
  title: string;
  icon?: string;
  /** Uno o más nodos (típicamente <ProductCard />), cada uno se renderiza como un slide */
  children: ReactNode[];
  /** Ancho de tarjeta en px, usado para calcular el desplazamiento por click */
  itemWidth?: number;
  emptyMessage?: string;
}

/**
 * Carrusel horizontal con scroll nativo + scroll-snap.
 * Usa overflow-x-auto real (no un slider simulado con transform), por lo que
 * funciona con touch/trackpad de forma nativa y además expone flechas para
 * navegación por click. Los botones se deshabilitan en los extremos según
 * la posición real de scroll (no un índice inventado).
 */
export function HorizontalCarousel({
  title,
  icon,
  children,
  itemWidth = 220,
  emptyMessage = "No hay elementos para mostrar por el momento.",
}: HorizontalCarouselProps) {
  const trackRef = useRef<HTMLDivElement | null>(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);

  const updateEdges = () => {
    const el = trackRef.current;
    if (!el) return;
    setAtStart(el.scrollLeft <= 4);
    setAtEnd(el.scrollLeft + el.clientWidth >= el.scrollWidth - 4);
  };

  useEffect(() => {
    updateEdges();
    const el = trackRef.current;
    if (!el) return;
    el.addEventListener("scroll", updateEdges, { passive: true });
    window.addEventListener("resize", updateEdges);
    return () => {
      el.removeEventListener("scroll", updateEdges);
      window.removeEventListener("resize", updateEdges);
    };
  }, [children.length]);

  const scrollByAmount = (direction: 1 | -1) => {
    const el = trackRef.current;
    if (!el) return;
    el.scrollBy({ left: direction * (itemWidth + 20) * 2, behavior: "smooth" });
  };

  return (
    <section className="w-full" aria-label={title}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-display text-2xl font-bold text-ink flex items-center gap-2">
          {icon && <span aria-hidden="true">{icon}</span>} {title}
        </h2>
        {children.length > 0 && (
          <div className="flex gap-2">
            <button
              type="button"
              aria-label="Desplazar a la izquierda"
              onClick={() => scrollByAmount(-1)}
              disabled={atStart}
              className="w-9 h-9 rounded-full border border-slate-300 bg-white flex items-center justify-center text-ink hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              ‹
            </button>
            <button
              type="button"
              aria-label="Desplazar a la derecha"
              onClick={() => scrollByAmount(1)}
              disabled={atEnd}
              className="w-9 h-9 rounded-full border border-slate-300 bg-white flex items-center justify-center text-ink hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              ›
            </button>
          </div>
        )}
      </div>

      {children.length === 0 ? (
        <p className="text-slate-500 text-sm">{emptyMessage}</p>
      ) : (
        <div
          ref={trackRef}
          className="flex gap-5 overflow-x-auto pb-2 snap-x snap-mandatory scroll-smooth [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          {children.map((child, i) => (
            <div key={i} className="snap-start shrink-0" style={{ width: itemWidth }}>
              {child}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
