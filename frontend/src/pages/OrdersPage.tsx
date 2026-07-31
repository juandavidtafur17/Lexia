import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";

interface OrderItem {
  id: string;
  product_title_snapshot: string;
  quantity: number;
  unit_price_snapshot: number;
}
interface Order {
  id: string;
  order_number: string;
  status: string;
  total_amount: number;
  currency: string;
  created_at: string;
  items: OrderItem[];
}

const STATUS_LABELS: Record<string, string> = {
  pending_payment: "Pendiente de pago",
  paid: "Pagado",
  processing: "En preparación",
  shipped: "Enviado",
  delivered: "Entregado",
  cancelled: "Cancelado",
  refunded: "Reembolsado",
  failed: "Fallido",
};

const STATUS_COLORS: Record<string, string> = {
  pending_payment: "bg-amber-100 text-amber-800",
  paid: "bg-blue-100 text-blue-800",
  processing: "bg-indigo-100 text-indigo-800",
  shipped: "bg-purple-100 text-purple-800",
  delivered: "bg-green-100 text-green-800",
  cancelled: "bg-slate-200 text-slate-700",
  refunded: "bg-orange-100 text-orange-800",
  failed: "bg-red-100 text-red-800",
};

export default function OrdersPage() {
  const { data: orders, isLoading } = useQuery({
    queryKey: ["orders"],
    queryFn: async () => {
      const { data } = await apiClient.get<Order[]>("/orders");
      return data;
    },
  });

  if (isLoading) return <p className="text-slate-500">Cargando pedidos...</p>;

  return (
    <div>
      <h1 className="font-display text-2xl font-bold mb-6">Mis pedidos</h1>
      {(!orders || orders.length === 0) && (
        <p className="text-slate-500">Aún no tienes pedidos registrados.</p>
      )}
      <div className="space-y-4">
        {orders?.map((order) => (
          <div key={order.id} className="border border-slate-200 rounded-lg p-5 bg-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-mono text-sm text-slate-500">{order.order_number}</p>
                <p className="text-xs text-slate-400">
                  {new Date(order.created_at).toLocaleString("es-PE")}
                </p>
              </div>
              <span
                className={`text-xs font-medium px-3 py-1 rounded-full ${STATUS_COLORS[order.status] ?? "bg-slate-100"}`}
              >
                {STATUS_LABELS[order.status] ?? order.status}
              </span>
            </div>

            <div className="mt-4 divide-y divide-slate-100">
              {order.items.map((item) => (
                <div key={item.id} className="flex justify-between py-2 text-sm">
                  <span>{item.product_title_snapshot} × {item.quantity}</span>
                  <span>${(item.unit_price_snapshot * item.quantity).toFixed(2)}</span>
                </div>
              ))}
            </div>

            <div className="flex justify-end mt-3">
              <p className="font-display font-bold text-lg">
                Total: ${order.total_amount.toFixed(2)} {order.currency}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
