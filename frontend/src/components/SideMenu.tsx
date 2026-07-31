import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiClient } from "@/api/client";
import { useAuthStore } from "@/store/authStore";

interface Category {
  id: string;
  name: string;
  slug: string;
}

interface SideMenuProps {
  open: boolean;
  onClose: () => void;
}

export function SideMenu({ open, onClose }: SideMenuProps) {
  const { user, logout } = useAuthStore();

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    enabled: open,
    queryFn: async () => {
      const { data } = await apiClient.get<Category[]>("/categories");
      return data;
    },
  });

  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-0 bg-black/50 z-50 transition-opacity ${
          open ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
      />

      <aside
        className={`fixed top-0 left-0 h-full w-[320px] bg-white z-50 shadow-xl transform transition-transform overflow-y-auto ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="bg-navy-900 text-white px-4 py-4 flex items-center justify-between sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <span className="text-lg">👤</span>
            <span className="font-semibold">
              {user ? `Hola, ${user.full_name.split(" ")[0]}` : "Hola, invitado"}
            </span>
          </div>
          <button onClick={onClose} aria-label="Cerrar menú" className="text-xl hover:text-accent-500">
            ✕
          </button>
        </div>

        {!user && (
          <div className="p-4 border-b border-slate-200">
            <Link
              to="/login"
              onClick={onClose}
              className="block text-center bg-accent-500 hover:bg-accent-600 text-navy-900 font-semibold py-2 rounded-md"
            >
              Iniciar sesión / Registrarme
            </Link>
          </div>
        )}

        <nav className="p-4">
          <h3 className="font-bold text-sm text-ink mb-2">Tienda por departamento</h3>
          <ul className="mb-6">
            {categories?.length ? (
              categories.map((c) => (
                <li key={c.id}>
                  <Link
                    to={`/?category_id=${c.id}`}
                    onClick={onClose}
                    className="flex items-center justify-between py-2 text-sm text-slate-700 hover:text-brand-600"
                  >
                    {c.name} <span>›</span>
                  </Link>
                </li>
              ))
            ) : (
              <li className="text-xs text-slate-400 py-2">Sin categorías disponibles todavía.</li>
            )}
            <li>
              <Link to="/" onClick={onClose} className="flex items-center justify-between py-2 text-sm text-brand-600 font-medium">
                Ver todo el catálogo <span>›</span>
              </Link>
            </li>
          </ul>

          <h3 className="font-bold text-sm text-ink mb-2">Vender en la plataforma</h3>
          <ul className="mb-6">
            <li>
              <Link to="/sell/new" onClick={onClose} className="flex items-center justify-between py-2 text-sm text-slate-700 hover:text-brand-600">
                Publicar un producto <span>›</span>
              </Link>
            </li>
          </ul>

          {user && (
            <>
              <h3 className="font-bold text-sm text-ink mb-2">Tu cuenta</h3>
              <ul className="mb-6">
                <li>
                  <Link to="/orders" onClick={onClose} className="flex items-center justify-between py-2 text-sm text-slate-700 hover:text-brand-600">
                    Tus pedidos <span>›</span>
                  </Link>
                </li>
                <li>
                  <Link to="/cart" onClick={onClose} className="flex items-center justify-between py-2 text-sm text-slate-700 hover:text-brand-600">
                    Tu carrito <span>›</span>
                  </Link>
                </li>
                {["admin", "super_admin", "warehouse_manager"].includes(user.role) && (
                  <li>
                    <Link to="/admin/inventory" onClick={onClose} className="flex items-center justify-between py-2 text-sm text-slate-700 hover:text-brand-600">
                      Panel de inventario <span>›</span>
                    </Link>
                  </li>
                )}
              </ul>

              <h3 className="font-bold text-sm text-ink mb-2">Ayuda y ajustes</h3>
              <ul>
                <li>
                  <button
                    onClick={() => {
                      logout();
                      onClose();
                    }}
                    className="w-full text-left py-2 text-sm text-red-600 hover:underline"
                  >
                    Cerrar sesión
                  </button>
                </li>
              </ul>
            </>
          )}
        </nav>
      </aside>
    </>
  );
}
