import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";

interface Warehouse {
  id: string;
  code: string;
  name: string;
  city: string;
}
interface StockItem {
  id: string;
  variant_id: string;
  quantity_on_hand: number;
  quantity_reserved: number;
}

export default function AdminInventoryPage() {
  const queryClient = useQueryClient();
  const [warehouseId, setWarehouseId] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<"disconnected" | "connected">("disconnected");

  const { data: warehouses } = useQuery({
    queryKey: ["warehouses"],
    queryFn: async () => {
      const { data } = await apiClient.get<Warehouse[]>("/inventory/warehouses");
      if (!warehouseId && data[0]) setWarehouseId(data[0].id);
      return data;
    },
  });

  const { data: stock, isLoading } = useQuery({
    queryKey: ["stock", warehouseId],
    enabled: !!warehouseId,
    queryFn: async () => {
      const { data } = await apiClient.get<StockItem[]>(`/inventory/warehouses/${warehouseId}/stock`);
      return data;
    },
  });

  const adjustStock = useMutation({
    mutationFn: (payload: { variant_id: string; warehouse_id: string; quantity_delta: number; reason: string }) =>
      apiClient.post("/inventory/adjust", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["stock", warehouseId] }),
  });

  // Suscripción en tiempo real: la tabla se actualiza sin recargar la página
  // cuando otro operador ajusta stock en el mismo almacén.
  useEffect(() => {
    if (!warehouseId) return;
    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${wsProtocol}://${window.location.host}/ws/inventory/${warehouseId}`);
    socket.onopen = () => setWsStatus("connected");
    socket.onclose = () => setWsStatus("disconnected");
    socket.onmessage = () => queryClient.invalidateQueries({ queryKey: ["stock", warehouseId] });
    return () => socket.close();
  }, [warehouseId, queryClient]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display text-2xl font-bold">Inventario en tiempo real</h1>
        <span className={`text-xs px-2 py-1 rounded-full ${wsStatus === "connected" ? "bg-green-100 text-green-700" : "bg-slate-200 text-slate-600"}`}>
          {wsStatus === "connected" ? "● En vivo" : "○ Reconectando"}
        </span>
      </div>

      <select
        value={warehouseId ?? ""}
        onChange={(e) => setWarehouseId(e.target.value)}
        className="border border-slate-300 rounded-md px-3 py-2 text-sm mb-6"
      >
        {warehouses?.map((w) => (
          <option key={w.id} value={w.id}>
            {w.name} ({w.code}) — {w.city}
          </option>
        ))}
      </select>

      {isLoading && <p className="text-slate-500">Cargando inventario...</p>}

      <table className="w-full text-sm border border-slate-200 rounded-lg overflow-hidden">
        <thead className="bg-ink text-white">
          <tr>
            <th className="text-left px-4 py-2">Variante (ID)</th>
            <th className="text-right px-4 py-2">Físico</th>
            <th className="text-right px-4 py-2">Reservado</th>
            <th className="text-right px-4 py-2">Disponible</th>
            <th className="text-right px-4 py-2">Ajuste</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {stock?.map((item) => {
            const available = item.quantity_on_hand - item.quantity_reserved;
            return (
              <tr key={item.id} className={available <= 5 ? "bg-signal/5" : ""}>
                <td className="px-4 py-2 font-mono text-xs">{item.variant_id.slice(0, 12)}...</td>
                <td className="px-4 py-2 text-right">{item.quantity_on_hand}</td>
                <td className="px-4 py-2 text-right">{item.quantity_reserved}</td>
                <td className={`px-4 py-2 text-right font-semibold ${available <= 5 ? "text-signal" : ""}`}>
                  {available}
                </td>
                <td className="px-4 py-2 text-right">
                  <button
                    onClick={() => {
                      const delta = prompt("Cantidad a ajustar (use negativo para restar):", "0");
                      if (!delta) return;
                      const reason = prompt("Motivo del ajuste (mínimo 3 caracteres):", "Ajuste manual");
                      if (!reason) return;
                      adjustStock.mutate({
                        variant_id: item.variant_id,
                        warehouse_id: warehouseId!,
                        quantity_delta: Number(delta),
                        reason,
                      });
                    }}
                    className="text-brand-600 hover:underline text-xs"
                  >
                    Ajustar
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
