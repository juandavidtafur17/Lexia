import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { apiClient } from "@/api/client";
import { useAuthStore } from "@/store/authStore";
import { Hero } from "@/components/Hero";
import { ProductCard } from "@/components/ProductCard";
import { HorizontalCarousel } from "@/components/HorizontalCarousel";
import { VerticalCarousel, type VerticalCarouselItem } from "@/components/VerticalCarousel";

interface Variant {
  id: string;
  price: number;
  currency: string;
}
interface Product {
  id: string;
  title: string;
  description: string;
  rating_average: number;
  rating_count: number;
  variants: Variant[];
}
interface Category {
  id: string;
  name: string;
  slug: string;
  parent_id: string | null;
  is_active: boolean;
}

export default function ProductsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get("q") ?? "";
  const categoryId = searchParams.get("category_id") ?? undefined;
  const [query, setQuery] = useState(initialQuery);
  const [page, setPage] = useState(1);
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const [addingId, setAddingId] = useState<string | null>(null);

  // Categorías reales del catálogo — alimentan el carrusel vertical de navegación.
  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: async () => {
      const { data } = await apiClient.get<Category[]>("/categories");
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });

  // Mejor valorados (sort=rating) — alimentan el carrusel horizontal de "Más vendidos".
  // Se piden aparte del grid principal porque su orden y su universo son distintos
  // (top-rated global vs. catálogo paginado/filtrado por búsqueda o categoría).
  const { data: topRated } = useQuery({
    queryKey: ["products", "top-rated"],
    queryFn: async () => {
      const { data } = await apiClient.get<Product[]>("/products", {
        params: { sort: "rating", page: 1, page_size: 12 },
      });
      return data;
    },
  });

  const { data: products, isLoading, isError } = useQuery({
    queryKey: ["products", query, page, categoryId],
    queryFn: async () => {
      const { data } = await apiClient.get<Product[]>("/products", {
        params: { q: query || undefined, page, page_size: 24, category_id: categoryId },
      });
      return data;
    },
  });

  const addToCart = useMutation({
    mutationFn: async (variantId: string) => apiClient.post("/cart/items", { variant_id: variantId, quantity: 1 }),
    onMutate: (variantId) => setAddingId(variantId),
    onSettled: () => setAddingId(null),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cart"] }),
  });

  const selectCategory = (id: string | undefined) => {
    setPage(1);
    const next = new URLSearchParams(searchParams);
    if (id) next.set("category_id", id);
    else next.delete("category_id");
    setSearchParams(next);
  };

  const renderProductCard = (p: Product) => (
    <ProductCard
      key={p.id}
      id={p.id}
      title={p.title}
      description={p.description}
      rating_average={p.rating_average}
      rating_count={p.rating_count}
      variants={p.variants}
      addingToCart={addingId === p.variants[0]?.id}
      onAddToCart={
        p.variants[0]
          ? () => (user ? addToCart.mutate(p.variants[0].id) : (window.location.href = "/login"))
          : undefined
      }
    />
  );

  const categoryItems: VerticalCarouselItem[] = [
    {
      id: "__all__",
      label: "Todas las categorías",
      icon: "🗂️",
      active: !categoryId,
      onSelect: () => selectCategory(undefined),
    },
    ...(categories ?? []).map((c) => ({
      id: c.id,
      label: c.name,
      icon: "🏷️",
      active: categoryId === c.id,
      onSelect: () => selectCategory(c.id),
    })),
  ];

  const highlights = [
    {
      title: "Operaciones claras",
      description: "Centraliza pedidos, inventario y pagos sin perder visibilidad del estado de cada proceso.",
      icon: "⚡",
    },
    {
      title: "Confianza del cliente",
      description: "Muestra productos, reseñas y disponibilidad con una experiencia más segura y elegante.",
      icon: "🛡️",
    },
    {
      title: "Decisiones rápidas",
      description: "Accede a métricas clave y acciones principales con menos fricción para el equipo.",
      icon: "📈",
    },
  ];

  return (
    <div className="-mx-4 md:-mx-4">
      <Hero />

      <div className="mx-auto max-w-7xl px-4 py-8 space-y-10">
        <div className="grid gap-4 md:grid-cols-3">
          {highlights.map((item) => (
            <div key={item.title} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="text-2xl">{item.icon}</div>
              <h3 className="mt-3 font-display text-lg font-semibold text-ink">{item.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p>
            </div>
          ))}
        </div>

        <HorizontalCarousel title="Operaciones destacadas" icon="⚡" itemWidth={210}>
          {(topRated ?? []).map((p) => renderProductCard(p))}
        </HorizontalCarousel>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-[260px_1fr]">
          {/* Carrusel vertical: navegación por categorías reales del catálogo */}
          <aside className="lg:sticky lg:top-4 lg:self-start">
            <VerticalCarousel title="Categorías" items={categoryItems} visibleCount={6} />
          </aside>

          <div id="trending">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
              <h2 className="flex items-center gap-2 font-display text-2xl font-bold text-ink">
                🛍️ Catálogo inteligente
              </h2>
              <input
                type="text"
                placeholder="Buscar productos..."
                value={query}
                onChange={(e) => {
                  setPage(1);
                  setQuery(e.target.value);
                }}
                className="w-72 rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            {isLoading && <p className="text-slate-500">Cargando catálogo...</p>}
            {isError && (
              <p className="text-red-600">
                No se pudo cargar el catálogo. Verifique que el backend esté activo.
              </p>
            )}

            <div className="grid grid-cols-2 md:grid-cols-3 gap-5">
              {products?.map((p) => renderProductCard(p))}
            </div>

            {products && products.length === 0 && (
              <p className="text-slate-500 mt-10 text-center">
                No se encontraron productos activos para esta búsqueda.
              </p>
            )}

            <div className="flex justify-center gap-3 mt-10">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-4 py-2 border rounded-md text-sm disabled:opacity-40"
              >
                Anterior
              </button>
              <span className="text-sm text-slate-500 self-center">Página {page}</span>
              <button
                onClick={() => setPage((p) => p + 1)}
                className="px-4 py-2 border rounded-md text-sm"
              >
                Siguiente
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
