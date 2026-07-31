import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { useCartStore } from "@/store/cartStore";
import { SideMenu } from "@/components/SideMenu";

const CATEGORIES = [
  "Todas las categorías",
  "Electrónica",
  "Hogar",
  "Belleza",
  "Deportes",
  "Bebés",
];

export function Navbar() {
  const { user, logout } = useAuthStore();
  const totalItems = useCartStore((s) => s.totalItems());
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [menuOpen, setMenuOpen] = useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    navigate(`/?q=${encodeURIComponent(search)}`);
  };

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-slate-950/95 backdrop-blur">
      <SideMenu open={menuOpen} onClose={() => setMenuOpen(false)} />

      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4">
        <button
          onClick={() => setMenuOpen(true)}
          aria-label="Abrir menú"
          className="shrink-0 text-xl text-white transition-colors hover:text-accent-500"
        >
          ☰
        </button>

        <Link to="/" className="flex shrink-0 items-center gap-2">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-accent-500/30 bg-accent-500/10 text-sm font-semibold text-accent-500">
            L
          </span>
          <span className="font-display text-lg font-semibold tracking-tight text-white">
            LEXIA<span className="text-accent-500">.</span>
          </span>
        </Link>

        <form onSubmit={handleSearch} className="hidden flex-1 md:flex">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="max-w-[180px] rounded-l-md border-r border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none"
          >
            {CATEGORIES.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar operaciones o productos"
            className="flex-1 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none"
          />
          <button
            type="submit"
            className="rounded-r-md bg-accent-500 px-5 py-2 text-sm font-semibold text-navy-900 transition-colors hover:bg-accent-600"
          >
            🔍 Buscar
          </button>
        </form>

        <div className="flex shrink-0 items-center gap-4 text-sm text-white">
          <Link to="/wishlist" className="transition-colors hover:text-accent-500" title="Favoritos">
            ♥
          </Link>

          <Link to="/cart" className="relative transition-colors hover:text-accent-500" title="Carrito">
            🛒
            {totalItems > 0 && (
              <span className="absolute -right-3 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-accent-500 text-[10px] font-bold text-navy-900">
                {totalItems}
              </span>
            )}
          </Link>

          {user ? (
            <button
              onClick={() => {
                logout();
                navigate("/login");
              }}
              className="text-slate-300 transition-colors hover:text-white"
            >
              Salir
            </button>
          ) : (
            <Link
              to="/login"
              className="rounded-md bg-accent-500 px-4 py-2 font-semibold text-navy-900 transition-colors hover:bg-accent-600"
            >
              Ingresar
            </Link>
          )}
        </div>
      </div>

      <div className="hidden border-t border-white/10 bg-white/95 md:block">
        <div className="mx-auto flex h-10 max-w-7xl items-center gap-6 px-4 text-sm text-slate-600">
          <Link to="/" className="font-medium text-accent-600 hover:text-accent-700">Inicio</Link>
          <Link to="/" className="hover:text-navy-900">Operaciones</Link>
          <Link to="/" className="hover:text-navy-900">Categorías</Link>
          <Link to="/orders" className="hover:text-navy-900">Panel de pedidos</Link>
          <Link to="/sell/new" className="font-medium text-accent-600 hover:text-accent-700">🏪 Vender</Link>
          {user && ["admin", "super_admin", "warehouse_manager"].includes(user.role) && (
            <Link to="/admin/inventory" className="hover:text-navy-900">Inventario</Link>
          )}
        </div>
      </div>
    </header>
  );
}
