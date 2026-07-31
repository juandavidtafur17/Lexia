import { useEffect, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/api/client";
import { useAuthStore } from "@/store/authStore";

interface Category {
  id: string;
  name: string;
}
interface VariantDraft {
  sku: string;
  price: string;
  weight_grams: string;
  color: string;
  size: string;
}

const emptyVariant = (): VariantDraft => ({ sku: "", price: "", weight_grams: "", color: "", size: "" });

type Step = 1 | 2 | 3 | 4 | 5;

export default function CreateListingPage() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>(1);
  const [error, setError] = useState<string | null>(null);
  const [publishedProductId, setPublishedProductId] = useState<string | null>(null);

  // --- Paso 2: alta de vendedor (solo si aún no existe perfil) ---
  const { data: sellerProfile, refetch: refetchSeller } = useQuery({
    queryKey: ["seller-profile"],
    enabled: !!user,
    retry: false,
    queryFn: async () => {
      try {
        const { data } = await apiClient.get("/sellers/me");
        return data;
      } catch {
        return null;
      }
    },
  });
  const [storeName, setStoreName] = useState("");
  const [taxId, setTaxId] = useState("");

  const applySeller = useMutation({
    mutationFn: () => apiClient.post("/sellers/apply", { store_name: storeName, tax_id: taxId }),
    onSuccess: async () => {
      await refetchSeller();
      setStep(3);
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? "No se pudo registrar el perfil de vendedor"),
  });

  // --- Paso 3: información del producto ---
  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: async () => {
      const { data } = await apiClient.get<Category[]>("/categories");
      return data;
    },
  });
  const [title, setTitle] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [brand, setBrand] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");

  // --- Paso 4: variantes ---
  const [variants, setVariants] = useState<VariantDraft[]>([emptyVariant()]);

  const updateVariant = (index: number, field: keyof VariantDraft, value: string) => {
    setVariants((prev) => prev.map((v, i) => (i === index ? { ...v, [field]: value } : v)));
  };

  const publish = useMutation({
    mutationFn: async () => {
      const payload = {
        title,
        description,
        category_id: categoryId,
        brand: brand || undefined,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        attributes: {},
        variants: variants.map((v) => ({
          sku: v.sku,
          price: Number(v.price),
          weight_grams: Number(v.weight_grams || 0),
          color: v.color || undefined,
          size: v.size || undefined,
        })),
      };
      const { data } = await apiClient.post("/products", payload);
      return data;
    },
    onSuccess: (data) => {
      setPublishedProductId(data.id);
      setStep(5);
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? "No se pudo publicar el producto"),
  });

  const canGoToInfo = !!sellerProfile;

  useEffect(() => {
    if (step === 2 && canGoToInfo) setStep(3);
  }, [step, canGoToInfo]);

  if (!user) {
    return (
      <div className="max-w-lg mx-auto mt-12 text-center">
        <p className="text-slate-600 mb-4">Debes iniciar sesión para publicar un producto.</p>
        <button
          onClick={() => navigate("/login")}
          className="bg-ink text-white px-6 py-2.5 rounded-md font-medium hover:bg-brand-700"
        >
          Iniciar sesión
        </button>
      </div>
    );
  }

  const stepLabels = ["Tipo", "Datos de vendedor", "Información", "Variantes y precio", "Publicado"];

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="font-display text-2xl font-bold mb-2">Crear publicación</h1>
      <div className="flex items-center gap-2 mb-8 text-xs text-slate-500">
        {stepLabels.map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            <span
              className={`w-6 h-6 rounded-full flex items-center justify-center font-semibold ${
                step === i + 1 ? "bg-brand-600 text-white" : i + 1 < step ? "bg-green-500 text-white" : "bg-slate-200"
              }`}
            >
              {i + 1 < step ? "✓" : i + 1}
            </span>
            <span className={step === i + 1 ? "text-ink font-medium" : ""}>{label}</span>
            {i < stepLabels.length - 1 && <span className="mx-1">—</span>}
          </div>
        ))}
      </div>

      {error && <p className="text-red-600 text-sm mb-4 bg-red-50 rounded-md p-3">{error}</p>}

      {/* Paso 1: elegir tipo de publicación (solo Producto físico está disponible en esta plataforma) */}
      {step === 1 && (
        <div>
          <h2 className="font-medium mb-4">Elige tipo de publicación</h2>
          <div className="grid grid-cols-3 gap-4">
            <button
              onClick={() => setStep(sellerProfile ? 3 : 2)}
              className="border-2 border-brand-600 rounded-lg p-5 text-center hover:bg-brand-50 transition-colors"
            >
              <div className="text-3xl mb-2">📦</div>
              <p className="font-semibold text-sm">Producto físico</p>
              <p className="text-xs text-slate-500 mt-1">Crea una publicación para vender uno o más productos.</p>
            </button>
            <div className="border rounded-lg p-5 text-center opacity-40 cursor-not-allowed">
              <div className="text-3xl mb-2">🚗</div>
              <p className="font-semibold text-sm">Vehículo</p>
              <p className="text-xs text-slate-500 mt-1">Próximamente</p>
            </div>
            <div className="border rounded-lg p-5 text-center opacity-40 cursor-not-allowed">
              <div className="text-3xl mb-2">🏠</div>
              <p className="font-semibold text-sm">Propiedad</p>
              <p className="text-xs text-slate-500 mt-1">Próximamente</p>
            </div>
          </div>
        </div>
      )}

      {/* Paso 2: alta de vendedor (una sola vez) */}
      {step === 2 && !canGoToInfo && (
        <div>
          <h2 className="font-medium mb-1">Activa tu cuenta de vendedor</h2>
          <p className="text-sm text-slate-500 mb-4">
            Solo se pide una vez. Con esto tus próximas publicaciones se crean directamente.
          </p>
          <div className="space-y-4 max-w-md">
            <div>
              <label className="text-sm font-medium text-slate-700">Nombre de tu tienda</label>
              <input
                value={storeName}
                onChange={(e) => setStoreName(e.target.value)}
                className="mt-1 w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">RUC / identificación tributaria</label>
              <input
                value={taxId}
                onChange={(e) => setTaxId(e.target.value)}
                className="mt-1 w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
              />
            </div>
            <button
              onClick={() => {
                setError(null);
                applySeller.mutate();
              }}
              disabled={applySeller.isPending || !storeName || !taxId}
              className="bg-ink text-white px-6 py-2.5 rounded-md font-medium hover:bg-brand-700 disabled:opacity-50"
            >
              {applySeller.isPending ? "Activando..." : "Activar cuenta de vendedor"}
            </button>
          </div>
        </div>
      )}

      {/* Paso 3: información del producto */}
      {step === 3 && (
        <div className="space-y-4 max-w-xl">
          <div>
            <label className="text-sm font-medium text-slate-700">Título</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
              placeholder="Ej: Auriculares inalámbricos con cancelación de ruido"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Categoría</label>
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              className="mt-1 w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="">Selecciona una categoría</option>
              {categories?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            {categories?.length === 0 && (
              <p className="text-xs text-amber-600 mt-1">
                Aún no hay categorías creadas — un administrador debe crearlas antes de publicar.
              </p>
            )}
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Marca (opcional)</label>
            <input
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              className="mt-1 w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Descripción</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              className="mt-1 w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Etiquetas (separadas por coma)</label>
            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="audio, inalámbrico, bluetooth"
              className="mt-1 w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
          <button
            onClick={() => (title && categoryId ? setStep(4) : setError("Completa el título y la categoría"))}
            className="bg-ink text-white px-6 py-2.5 rounded-md font-medium hover:bg-brand-700"
          >
            Continuar
          </button>
        </div>
      )}

      {/* Paso 4: variantes / precio / inventario base */}
      {step === 4 && (
        <div>
          <h2 className="font-medium mb-4">Variantes y precio</h2>
          <div className="space-y-4">
            {variants.map((v, i) => (
              <div key={i} className="border border-slate-200 rounded-lg p-4 grid grid-cols-5 gap-3">
                <div>
                  <label className="text-xs text-slate-600">SKU</label>
                  <input
                    value={v.sku}
                    onChange={(e) => updateVariant(i, "sku", e.target.value)}
                    className="mt-1 w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-600">Precio (USD)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={v.price}
                    onChange={(e) => updateVariant(i, "price", e.target.value)}
                    className="mt-1 w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-600">Peso (g)</label>
                  <input
                    type="number"
                    value={v.weight_grams}
                    onChange={(e) => updateVariant(i, "weight_grams", e.target.value)}
                    className="mt-1 w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-600">Color</label>
                  <input
                    value={v.color}
                    onChange={(e) => updateVariant(i, "color", e.target.value)}
                    className="mt-1 w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm"
                  />
                </div>
                <div className="flex items-end gap-2">
                  <div className="flex-1">
                    <label className="text-xs text-slate-600">Talla</label>
                    <input
                      value={v.size}
                      onChange={(e) => updateVariant(i, "size", e.target.value)}
                      className="mt-1 w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm"
                    />
                  </div>
                  {variants.length > 1 && (
                    <button
                      onClick={() => setVariants((prev) => prev.filter((_, idx) => idx !== i))}
                      className="text-red-600 text-xs pb-2"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <button
            onClick={() => setVariants((prev) => [...prev, emptyVariant()])}
            className="text-brand-600 text-sm font-medium mt-3 hover:underline"
          >
            + Añadir otra variante
          </button>

          <div className="flex gap-3 mt-6">
            <button onClick={() => setStep(3)} className="px-6 py-2.5 rounded-md border text-sm font-medium">
              Atrás
            </button>
            <button
              onClick={() => {
                const valid = variants.every((v) => v.sku && Number(v.price) > 0);
                if (!valid) {
                  setError("Cada variante necesita al menos SKU y un precio mayor a 0");
                  return;
                }
                setError(null);
                publish.mutate();
              }}
              disabled={publish.isPending}
              className="bg-accent-500 hover:bg-accent-600 text-navy-900 px-6 py-2.5 rounded-md font-semibold disabled:opacity-50"
            >
              {publish.isPending ? "Publicando..." : "Publicar producto"}
            </button>
          </div>
        </div>
      )}

      {/* Paso 5: confirmación real de publicación */}
      {step === 5 && publishedProductId && (
        <div className="text-center py-10">
          <div className="text-5xl mb-4">✅</div>
          <h2 className="font-display text-xl font-bold mb-2">¡Tu producto ya está publicado!</h2>
          <p className="text-slate-500 mb-6">Ya es visible en el catálogo del marketplace.</p>
          <div className="flex justify-center gap-3">
            <button
              onClick={() => navigate(`/products/${publishedProductId}`)}
              className="bg-ink text-white px-6 py-2.5 rounded-md font-medium hover:bg-brand-700"
            >
              Ver mi publicación
            </button>
            <button
              onClick={() => {
                setStep(1);
                setTitle("");
                setDescription("");
                setBrand("");
                setTags("");
                setCategoryId("");
                setVariants([emptyVariant()]);
                setPublishedProductId(null);
              }}
              className="px-6 py-2.5 rounded-md border text-sm font-medium"
            >
              Publicar otro producto
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
