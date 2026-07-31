import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/api/client";

const schema = z.object({
  full_name: z.string().min(2, "Ingrese su nombre completo"),
  email: z.string().email("Correo inválido"),
  password: z
    .string()
    .min(10, "Mínimo 10 caracteres")
    .regex(/[A-Z]/, "Debe incluir una mayúscula")
    .regex(/[0-9]/, "Debe incluir un número"),
  country_code: z.string().length(2, "Use el código ISO de 2 letras (ej: PE, US, MX)"),
});
type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });
  const [serverError, setServerError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await apiClient.post("/auth/register", { ...values, country_code: values.country_code.toUpperCase() });
      setSuccess(true);
      setTimeout(() => navigate("/login"), 1500);
    } catch (err: any) {
      setServerError(err?.response?.data?.detail ?? "Error al registrar la cuenta");
    }
  };

  return (
    <div className="max-w-md mx-auto mt-12 bg-white rounded-xl border border-slate-200 p-8">
      <h1 className="font-display text-2xl font-bold mb-6">Crear cuenta</h1>
      {success ? (
        <p className="text-green-700 bg-green-50 rounded-md p-3 text-sm">
          Cuenta creada correctamente. Redirigiendo al inicio de sesión...
        </p>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {[
            { name: "full_name" as const, label: "Nombre completo", type: "text" },
            { name: "email" as const, label: "Correo electrónico", type: "email" },
            { name: "password" as const, label: "Contraseña", type: "password" },
            { name: "country_code" as const, label: "País (código ISO, ej: PE)", type: "text" },
          ].map((f) => (
            <div key={f.name}>
              <label className="text-sm font-medium text-slate-700">{f.label}</label>
              <input
                type={f.type}
                {...register(f.name)}
                className="mt-1 w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
              />
              {errors[f.name] && (
                <p className="text-red-600 text-xs mt-1">{errors[f.name]?.message}</p>
              )}
            </div>
          ))}
          {serverError && <p className="text-red-600 text-sm">{serverError}</p>}
          <button
            type="submit"
            className="w-full bg-ink text-white rounded-md py-2.5 font-medium hover:bg-brand-700 transition-colors"
          >
            Registrarme
          </button>
        </form>
      )}
    </div>
  );
}
