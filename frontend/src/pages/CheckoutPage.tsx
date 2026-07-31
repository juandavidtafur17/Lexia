import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { Elements, PaymentElement, useStripe, useElements } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";
import { apiClient } from "@/api/client";

const stripePromise = import.meta.env.VITE_STRIPE_PUBLIC_KEY
  ? loadStripe(import.meta.env.VITE_STRIPE_PUBLIC_KEY)
  : null;

const addressSchema = z.object({
  recipient_name: z.string().min(2, "Requerido"),
  line1: z.string().min(3, "Requerido"),
  line2: z.string().optional(),
  city: z.string().min(2, "Requerido"),
  state: z.string().min(2, "Requerido"),
  postal_code: z.string().min(3, "Requerido"),
  country_code: z.string().length(2, "Código ISO de 2 letras"),
  phone_number: z.string().optional(),
});
const checkoutSchema = z.object({
  shipping_address: addressSchema,
  billing_address: addressSchema,
  coupon_code: z.string().optional(),
});
type CheckoutForm = z.infer<typeof checkoutSchema>;

function PaymentStep({ clientSecret, orderId }: { clientSecret: string; orderId: string }) {
  const stripe = useStripe();
  const elements = useElements();
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const navigate = useNavigate();

  const handlePay = async () => {
    if (!stripe || !elements) return;
    setProcessing(true);
    setError(null);
    const { error: confirmError } = await stripe.confirmPayment({
      elements,
      confirmParams: { return_url: `${window.location.origin}/orders` },
      redirect: "if_required",
    });
    if (confirmError) {
      setError(confirmError.message ?? "Error procesando el pago");
      setProcessing(false);
      return;
    }
    navigate("/orders");
  };

  return (
    <div className="mt-6">
      <PaymentElement />
      {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
      <button
        onClick={handlePay}
        disabled={processing}
        className="w-full mt-4 bg-ink text-white rounded-md py-3 font-medium hover:bg-brand-700 transition-colors disabled:opacity-50"
      >
        {processing ? "Procesando pago..." : "Pagar ahora"}
      </button>
    </div>
  );
}

export default function CheckoutPage() {
  const { register, handleSubmit, watch, formState: { errors } } = useForm<CheckoutForm>({
    resolver: zodResolver(checkoutSchema),
  });
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [orderId, setOrderId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sameAsShipping = watch("billing_address");

  const onSubmit = async (values: CheckoutForm) => {
    setError(null);
    try {
      const { data: order } = await apiClient.post("/orders", values);
      const { data: intent } = await apiClient.post(`/payments/orders/${order.id}/create-intent`);
      setClientSecret(intent.client_secret);
      setOrderId(order.id);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "No se pudo crear el pedido");
    }
  };

  if (clientSecret && orderId && stripePromise) {
    return (
      <div className="max-w-lg mx-auto">
        <h1 className="font-display text-2xl font-bold mb-6">Pago seguro</h1>
        <Elements stripe={stripePromise} options={{ clientSecret }}>
          <PaymentStep clientSecret={clientSecret} orderId={orderId} />
        </Elements>
      </div>
    );
  }

  const addressFields: Array<{ name: keyof z.infer<typeof addressSchema>; label: string }> = [
    { name: "recipient_name", label: "Nombre del destinatario" },
    { name: "line1", label: "Dirección" },
    { name: "city", label: "Ciudad" },
    { name: "state", label: "Región/Estado" },
    { name: "postal_code", label: "Código postal" },
    { name: "country_code", label: "País (ISO, ej: PE)" },
  ];

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="font-display text-2xl font-bold mb-6">Finalizar compra</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
        <section>
          <h2 className="font-medium mb-3">Dirección de envío</h2>
          <div className="grid grid-cols-2 gap-3">
            {addressFields.map((f) => (
              <div key={f.name}>
                <label className="text-xs text-slate-600">{f.label}</label>
                <input
                  {...register(`shipping_address.${f.name}`)}
                  className="mt-1 w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="font-medium mb-3">Dirección de facturación</h2>
          <div className="grid grid-cols-2 gap-3">
            {addressFields.map((f) => (
              <div key={f.name}>
                <label className="text-xs text-slate-600">{f.label}</label>
                <input
                  {...register(`billing_address.${f.name}`)}
                  className="mt-1 w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
            ))}
          </div>
        </section>

        <div>
          <label className="text-sm font-medium text-slate-700">Cupón de descuento (opcional)</label>
          <input
            {...register("coupon_code")}
            className="mt-1 w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
          />
        </div>

        {error && <p className="text-red-600 text-sm">{error}</p>}

        <button
          type="submit"
          className="w-full bg-ink text-white rounded-md py-3 font-medium hover:bg-brand-700 transition-colors"
        >
          Confirmar pedido y continuar al pago
        </button>
      </form>
    </div>
  );
}
