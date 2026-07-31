import { useEffect, useRef, useState } from "react";

export interface CarouselSlide {
  id: string;
  eyebrow?: string;
  title: string;
  description?: string;
  ctaLabel?: string;
  ctaHref?: string;
  background: string; // clases Tailwind de fondo (gradiente/color)
}

interface CarouselProps {
  slides: CarouselSlide[];
  autoPlayMs?: number;
}

export function Carousel({ slides, autoPlayMs = 5000 }: CarouselProps) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (paused || slides.length <= 1) return;
    timerRef.current = setInterval(() => {
      setIndex((i) => (i + 1) % slides.length);
    }, autoPlayMs);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [paused, slides.length, autoPlayMs]);

  if (slides.length === 0) return null;
  const slide = slides[index];

  const goTo = (i: number) => setIndex(((i % slides.length) + slides.length) % slides.length);

  return (
    <div
      className="relative overflow-hidden"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <div className={`${slide.background} transition-colors duration-500`}>
        <div className="max-w-5xl mx-auto px-4 py-14 text-center text-white">
          {slide.eyebrow && (
            <span className="inline-block bg-navy-700/80 text-accent-500 text-xs font-semibold tracking-wide px-3 py-1 rounded-full mb-5">
              {slide.eyebrow}
            </span>
          )}
          <h1 className="font-display text-3xl md:text-4xl font-bold leading-tight">{slide.title}</h1>
          {slide.description && (
            <p className="text-slate-200 mt-4 max-w-2xl mx-auto text-sm md:text-base">{slide.description}</p>
          )}
          {slide.ctaLabel && slide.ctaHref && (
            <a
              href={slide.ctaHref}
              className="inline-block mt-7 bg-accent-500 hover:bg-accent-600 text-navy-900 font-semibold px-6 py-3 rounded-md transition-colors"
            >
              {slide.ctaLabel}
            </a>
          )}
        </div>
      </div>

      {slides.length > 1 && (
        <>
          <button
            aria-label="Diapositiva anterior"
            onClick={() => goTo(index - 1)}
            className="absolute left-3 top-1/2 -translate-y-1/2 bg-black/30 hover:bg-black/50 text-white w-9 h-9 rounded-full flex items-center justify-center transition-colors"
          >
            ‹
          </button>
          <button
            aria-label="Siguiente diapositiva"
            onClick={() => goTo(index + 1)}
            className="absolute right-3 top-1/2 -translate-y-1/2 bg-black/30 hover:bg-black/50 text-white w-9 h-9 rounded-full flex items-center justify-center transition-colors"
          >
            ›
          </button>

          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-2">
            {slides.map((s, i) => (
              <button
                key={s.id}
                aria-label={`Ir a la diapositiva ${i + 1}`}
                onClick={() => goTo(i)}
                className={`h-1.5 rounded-full transition-all ${
                  i === index ? "w-6 bg-accent-500" : "w-1.5 bg-white/50 hover:bg-white/80"
                }`}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
