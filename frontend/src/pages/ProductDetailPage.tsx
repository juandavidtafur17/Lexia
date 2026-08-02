import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
interface Review {
  id: string;
  rating: number;
  title: string | null;
  comment: string;
  is_verified_purchase: boolean;
  ai_sentiment_summary: string | null;
  created_at: string;
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
  const [reviewComment, setReviewComment] = useState("");
  const [reviewTitle, setReviewTitle] = useState("");
  const [reviewRating, setReviewRating] = useState(5);
  const queryClient = useQueryClient();

  const { data: product, isLoading } = useQuery({
    queryKey: ["product", id],
    queryFn: async () => {
      const { data } = await apiClient.get<Product>(`/products/${id}`);
      if (!selectedVariant && data.variants[0]) setSelectedVariant(data.variants[0].id);
      return data;
    },
  });

  const { data: reviews, isLoading: reviewsLoading } = useQuery({
    queryKey: ["productReviews", id],
    queryFn: async () => {
      const { data } = await apiClient.get<Review[]>(`/reviews/products/${id}`);
      return data;
    },
    enabled: Boolean(id),
  });

  const reviewSummary = useMemo(() => {
    if (!reviews || reviews.length === 0) return null;
    const complete = reviews.filter((review) => review.ai_sentiment_summary);
    if (complete.length === 0) return "Los resúmenes de IA se están generando en segundo plano.";
    return complete[0].ai_sentiment_summary;
  }, [reviews]);

  const averageRating = useMemo(() => {
    if (!reviews || reviews.length === 0) return null;
    const total = reviews.reduce((sum, review) => sum + review.rating, 0);
    return (total / reviews.length).toFixed(1);
  }, [reviews]);

  const addToCart = useMutation({
    mutationFn: async () => {
      if (!selectedVariant) throw new Error("Seleccione una variante");
      return apiClient.post("/cart/items", { variant_id: selectedVariant, quantity });
    },
    onSuccess: () => setFeedback("Producto añadido al carrito."),
    onError: (err: any) => setFeedback(err?.response?.data?.detail ?? "No se pudo añadir al carrito."),
  });

  const submitReview = useMutation({
    mutationFn: async () => {
      if (!id) throw new Error("Producto inválido");
      return apiClient.post("/reviews", {
        product_id: id,
        rating: reviewRating,
        title: reviewTitle,
        comment: reviewComment,
      });
    },
    onSuccess: () => {
      setFeedback("Reseña enviada. El resumen IA se generará en pocos segundos.");
      setReviewComment("");
      setReviewTitle("");
      setReviewRating(5);
      if (id) {
        queryClient.invalidateQueries({ queryKey: ["productReviews", id] });
      }
    },
    onError: (err: any) => setFeedback(err?.response?.data?.detail ?? "No se pudo enviar la reseña."),
  });

  if (isLoading || reviewsLoading) return <p className="text-slate-500">Cargando producto...</p>;
  if (!product) return <p className="text-red-600">Producto no encontrado.</p>;

  const variant = product.variants.find((v) => v.id === selectedVariant);

  return (
    <div className="space-y-10">
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

          {user ? (
            <div className="mt-8 rounded-3xl border border-slate-200 bg-slate-50 p-6">
              <h3 className="text-lg font-semibold text-slate-900">Escribe tu reseña</h3>
              <p className="text-sm text-slate-500 mt-2">Comparte tu experiencia y deja que la inteligencia artificial genere un resumen profesional.</p>

              <div className="mt-4 grid gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700">Título de la reseña</label>
                  <input
                    value={reviewTitle}
                    onChange={(e) => setReviewTitle(e.target.value)}
                    className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                    placeholder="Ej. Calidad sobresaliente"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700">Calificación</label>
                  <select
                    value={reviewRating}
                    onChange={(e) => setReviewRating(Number(e.target.value))}
                    className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    {[5, 4, 3, 2, 1].map((value) => (
                      <option key={value} value={value}>
                        {value} estrella{value > 1 ? "s" : ""}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700">Comentario</label>
                  <textarea
                    value={reviewComment}
                    onChange={(e) => setReviewComment(e.target.value)}
                    className="mt-2 h-28 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm resize-none"
                    placeholder="Describe tu experiencia con el producto"
                  />
                </div>
                <button
                  onClick={() => submitReview.mutate()}
                  disabled={submitReview.isPending || !reviewComment.trim()}
                  className="w-full rounded-md bg-brand-700 px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                >
                  {submitReview.isPending ? "Enviando reseña..." : "Enviar reseña"}
                </button>
              </div>
            </div>
          ) : (
            <div className="mt-8 rounded-3xl border border-slate-200 bg-slate-50 p-6">
              <p className="text-slate-700">Inicia sesión para dejar una reseña y activar el resumen generado por IA.</p>
            </div>
          )}
        </div>
      </div>

      <section className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Evaluaciones de clientes</p>
            <h2 className="text-xl font-semibold">Reseñas y análisis de IA</h2>
          </div>
          {averageRating ? (
            <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700">
              Rating promedio: {averageRating} / 5 ({reviews?.length ?? 0} reseñas)
            </div>
          ) : (
            <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700">
              Sin reseñas aún
            </div>
          )}
        </div>

        <div className="mt-6 space-y-6">
          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
            <p className="text-sm font-semibold text-slate-900">Resumen profesional generado por IA</p>
            <p className="mt-3 text-slate-700">{reviewSummary ?? "No hay resúmenes disponibles aún."}</p>
          </div>

          {reviews && reviews.length > 0 ? (
            reviews.map((review) => (
              <div key={review.id} className="rounded-3xl border border-slate-200 p-5">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="font-semibold text-slate-900">{review.title || "Reseña del cliente"}</p>
                    <p className="text-sm text-slate-500">Rating: {review.rating} / 5</p>
                  </div>
                  <span className="text-xs uppercase tracking-[0.2em] text-slate-500">
                    {review.is_verified_purchase ? "Compra verificada" : "No verificada"}
                  </span>
                </div>
                <p className="mt-4 text-slate-700">{review.comment}</p>
                <div className="mt-4 rounded-2xl bg-slate-100 p-4">
                  <p className="text-sm font-semibold text-slate-900">Resumen IA</p>
                  <p className="mt-2 text-slate-700">
                    {review.ai_sentiment_summary ?? "Resumen en cola; se generará en breve."}
                  </p>
                </div>
              </div>
            ))
          ) : (
            <p className="text-slate-600">Aún no hay reseñas disponibles para este producto.</p>
          )}
        </div>
      </section>
    </div>
  );
}
