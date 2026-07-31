import { useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { apiClient } from "@/api/client";

interface CartItem {
  id: string;
  variant_id: string;
  quantity: number;
}

export default function CartPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data: items, isLoading } = useQuery({
    queryKey: ["cart"],
    queryFn: async () => {
      const { data } = await apiClient.get<CartItem[]>("/cart");
      return data;
    },
  });

  const updateQuantity = useMutation({
    mutationFn: ({ id, quantity }: { id: string; quantity: number }) =>
      apiClient.patch(`/cart/items/${id}`, null, { params: { quantity } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cart"] }),
  });

  const removeItem = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/cart/items/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cart"] }),
  });

  useEffect(() => {
    document.title = "Carrito — ERP Marketplace";
  }, []);

  if (isLoading) return <p className="text-slate-500">Cargando carrito...</p>;

  if (!items || items.length === 0) {
    return (
      <div className="text-center py-20">
        <p className="text-slate-500 mb-4">Tu carrito está vacío.</p>
        <Link to="/" className="text-brand-600 font-medium hover:underline">
          Explorar catálogo
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h1 className="font-display text-2xl font-bold mb-6">Carrito de compras</h1>
      <div className="space-y-3">
        {items.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between border border-slate-200 rounded-lg p-4 bg-white"
          >
            <div>
              <p className="font-medium text-sm">SKU vinculado: {item.variant_id.slice(0, 8)}...</p>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min={1}
                value={item.quantity}
                onChange={(e) =>
                  updateQuantity.mutate({ id: item.id, quantity: Math.max(1, Number(e.target.value)) })
                }
                className="w-16 border border-slate-300 rounded-md px-2 py-1 text-sm"
              />
              <button
                onClick={() => removeItem.mutate(item.id)}
                className="text-red-600 text-sm hover:underline"
              >
                Eliminar
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 flex justify-end">
        <button
          onClick={() => navigate("/checkout")}
          className="bg-ink text-white rounded-md px-6 py-3 font-medium hover:bg-brand-700 transition-colors"
        >
          Continuar al pago
        </button>
      </div>
    </div>
  );
}
