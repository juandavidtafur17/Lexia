import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { useAuthStore } from "@/store/authStore";

interface Variant {
  id: string;
  sku: string;
  color: string | null;
  size: string | null;
  price: number;
  is_active: boolean;
}
interface Product {
  id: string;
  title: string;
  description: string;
  brand: string | null;
  variants: Variant[];
}

export default function ProductDetailPage() {
  const { id } = useParams();
  const user = useAuthStore((s) => s.user);
  const [selectedVariant, setSelectedVariant] = useState<string | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [feedback, setFeedback] = useState<string | null>(null);

  const { data: product, isLoading } = useQuery({
    queryKey: ["product", id],
    queryFn: async () => {
      const { data } = await apiClient.get<Product>(`/products/${id}`);
      if (!selectedVariant && data.variants[0]) setSelectedVariant(data.variants[0].id);
      return data;
    },
  });

  const addToCart = useMutation({
    mutationFn: async () => {
      if (!selectedVariant) throw new Error("Seleccione una variante");
      return apiClient.post("/cart/items", { variant_id: selectedVariant, quantity });
    },
    onSuccess: () => setFeedback("Producto añadido al carrito."),
    onError: (err: any) => setFeedback(err?.response?.data?.detail ?? "No se pudo añadir al carrito."),
  });

  if (isLoading) return <p className="text-slate-500">Cargando producto...</p>;
  if (!product) return <p className="text-red-600">Producto no encontrado.</p>;

  const variant = product.variants.find((v) => v.id === selectedVariant);

  return (
    <div className="grid md:grid-cols-2 gap-10">
      <div className="aspect-square bg-slate-100 rounded-xl" />
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-500">{product.brand ?? "Marketplace"}</p>
        <h1 className="font-display text-3xl font-bold mt-1">{product.title}</h1>
        <p className="text-slate-600 mt-4 leading-relaxed">{product.description}</p>

        <div className="mt-6">
          <label className="text-sm font-medium text-slate-700">Variante</label>
          <select
            value={selectedVariant ?? ""}
            onChange={(e) => setSelectedVariant(e.target.value)}
            className="mt-1 w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
          >
            {product.variants.map((v) => (
              <option key={v.id} value={v.id} disabled={!v.is_active}>
                {[v.color, v.size].filter(Boolean).join(" / ") || v.sku} — ${v.price}
              </option>
            ))}
          </select>
        </div>

        {variant && (
          <p className="font-display text-3xl font-bold text-brand-700 mt-4">${variant.price.toFixed(2)}</p>
        )}

        <div className="flex items-center gap-3 mt-4">
          <input
            type="number"
            min={1}
            value={quantity}
            onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))}
            className="w-20 border border-slate-300 rounded-md px-2 py-2 text-sm"
          />
          <button
            onClick={() => (user ? addToCart.mutate() : (window.location.href = "/login"))}
            disabled={addToCart.isPending}
            className="flex-1 bg-ink text-white rounded-md py-2.5 font-medium hover:bg-brand-700 transition-colors"
          >
            {addToCart.isPending ? "Añadiendo..." : "Añadir al carrito"}
          </button>
        </div>
        {feedback && <p className="text-sm mt-3 text-slate-600">{feedback}</p>}
      </div>
    </div>
  );
}
