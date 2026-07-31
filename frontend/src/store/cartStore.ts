import { create } from "zustand";

export interface CartLine {
  id: string;
  variant_id: string;
  quantity: number;
  title?: string;
  price?: number;
}

interface CartState {
  items: CartLine[];
  setItems: (items: CartLine[]) => void;
  updateQuantityLocal: (id: string, quantity: number) => void;
  removeItemLocal: (id: string) => void;
  totalItems: () => number;
  subtotal: () => number;
}

export const useCartStore = create<CartState>((set, get) => ({
  items: [],
  setItems: (items) => set({ items }),
  updateQuantityLocal: (id, quantity) =>
    set((state) => ({
      items: state.items.map((i) => (i.id === id ? { ...i, quantity } : i)),
    })),
  removeItemLocal: (id) => set((state) => ({ items: state.items.filter((i) => i.id !== id) })),
  totalItems: () => get().items.reduce((acc, i) => acc + i.quantity, 0),
  subtotal: () => get().items.reduce((acc, i) => acc + (i.price ?? 0) * i.quantity, 0),
}));
