import { Link } from "react-router-dom";
import { StarRating } from "@/components/StarRating";

interface Variant {
  id: string;
  price: number;
}
interface ProductCardProps {
  id: string;
  title: string;
  description?: string;
  rating_average: number;
  rating_count: number;
  variants: Variant[];
  imageUrl?: string;
  onAddToCart?: () => void;
  addingToCart?: boolean;
}

export function ProductCard({
  id,
  title,
  description,
  rating_average,
  rating_count,
  variants,
  imageUrl,
  onAddToCart,
  addingToCart,
}: ProductCardProps) {
  const minPrice = variants.length ? Math.min(...variants.map((v) => v.price)) : null;

  return (
    <div className="bg-white border border-slate-200 rounded-lg overflow-hidden hover:shadow-lg hover:-translate-y-0.5 transition-all flex flex-col">
      <Link to={`/products/${id}`} className="block bg-slate-50 aspect-square flex items-center justify-center overflow-hidden">
        {imageUrl ? (
          <img src={imageUrl} alt={title} className="w-full h-full object-cover" />
        ) : (
          <span className="text-slate-300 text-4xl">📦</span>
        )}
      </Link>

      <div className="p-3 flex flex-col flex-1">
        <Link to={`/products/${id}`}>
          <h3 className="font-medium text-sm text-ink line-clamp-2 min-h-[2.5rem] hover:text-brand-600">
            {title}
          </h3>
        </Link>
        {description && (
          <p className="text-xs text-slate-400 line-clamp-1 mt-1">{description}</p>
        )}

        <div className="mt-2">
          <StarRating value={rating_average} count={rating_count} />
        </div>

        <p className="font-display font-bold text-lg text-ink mt-2">
          {minPrice !== null ? `$${minPrice.toFixed(2)}` : "Sin stock"}
        </p>

        <div className="mt-auto pt-3 space-y-2">
          {onAddToCart ? (
            <button
              onClick={onAddToCart}
              disabled={addingToCart || minPrice === null}
              className="w-full bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-sm font-semibold py-2 rounded-md transition-colors"
            >
              🛒 {addingToCart ? "Añadiendo..." : "Añadir al carrito"}
            </button>
          ) : (
            <Link
              to={`/products/${id}`}
              className="block text-center w-full bg-accent-500 hover:bg-accent-600 text-navy-900 text-sm font-semibold py-2 rounded-md transition-colors"
            >
              Ver producto
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
