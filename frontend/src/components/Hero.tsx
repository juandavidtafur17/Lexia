export function Hero() {
  return (
    <section className="relative overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(37,99,235,0.25),_transparent_45%),linear-gradient(135deg,_#071426_0%,_#122340_45%,_#0f172a_100%)]">
      <div className="absolute inset-0 bg-[linear-gradient(90deg,_rgba(255,255,255,0.08)_1px,_transparent_1px),linear-gradient(rgba(255,255,255,0.05)_1px,_transparent_1px)] bg-[size:42px_42px] opacity-20" />
      <div className="relative mx-auto max-w-7xl px-4 py-16 lg:py-24">
        <div className="grid items-center gap-10 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="max-w-2xl">
            <span className="inline-flex items-center rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.25em] text-accent-500 backdrop-blur">
              Plataforma LEXIA
            </span>
            <h1 className="mt-5 font-display text-4xl font-semibold leading-tight text-white sm:text-5xl">
              Controla ventas, inventario y confianza con una experiencia más premium.
            </h1>
            <p className="mt-5 text-lg leading-8 text-slate-300">
              La nueva capa operativa para vender con más velocidad, visualizar cada etapa del negocio y tomar decisiones con claridad desde un solo punto de mando.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a href="#trending" className="rounded-full bg-accent-500 px-5 py-3 font-semibold text-navy-900 transition-colors hover:bg-accent-600">
                Explorar catálogo
              </a>
              <a href="/sell/new" className="rounded-full border border-white/20 bg-white/10 px-5 py-3 font-semibold text-white transition-colors hover:bg-white/20">
                Crear nueva operación
              </a>
            </div>
            <div className="mt-8 flex flex-wrap gap-3 text-sm text-slate-300">
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">⚡ Respuesta inmediata</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">🔒 Procesos confiables</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">📈 Visión global</span>
            </div>
          </div>

          <div className="relative">
            <div className="absolute inset-0 translate-x-6 translate-y-6 rounded-[2rem] bg-accent-500/20 blur-3xl" />
            <div className="relative rounded-[2rem] border border-white/10 bg-slate-950/70 p-4 shadow-2xl shadow-slate-950/50 backdrop-blur-xl">
              <div className="rounded-[1.5rem] border border-white/10 bg-gradient-to-br from-brand-600 via-slate-800 to-accent-500 p-5">
                <div className="flex items-center justify-between text-sm text-white/80">
                  <span className="font-semibold">Panel operativo</span>
                  <span className="rounded-full bg-white/15 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.2em]">
                    Live
                  </span>
                </div>

                <div className="mt-5 rounded-[1.25rem] border border-white/15 bg-slate-950/60 p-4 text-white">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Rendimiento</p>
                      <p className="mt-1 text-3xl font-semibold">+28%</p>
                    </div>
                    <div className="rounded-2xl border border-accent-500/30 bg-accent-500/15 px-3 py-2 text-right text-sm text-accent-400">
                      <p className="font-semibold">Inventario</p>
                      <p>97% saludable</p>
                    </div>
                  </div>

                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    {[
                      ["Reservas automáticas", "Sin fricción"],
                      ["Alertas tempranas", "Conectadas"],
                      ["Seguimiento", "Tiempo real"],
                      ["Documentos", "Centralizados"],
                    ].map(([label, value]) => (
                      <div key={label} className="rounded-2xl border border-white/10 bg-white/5 p-3">
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{label}</p>
                        <p className="mt-1 text-sm font-semibold text-white">{value}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
