import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/api/client";
import { useAuthStore } from "@/store/authStore";

const schema = z.object({
  email: z.string().email("Correo inválido"),
  password: z.string().min(1, "La contraseña es obligatoria"),
  mfa_code: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });
  const [serverError, setServerError] = useState<string | null>(null);
  const [needsMfa, setNeedsMfa] = useState(false);
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);
  const navigate = useNavigate();

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      const { data } = await apiClient.post("/auth/login", values);
      setTokens(data.access_token, data.refresh_token);
      const me = await apiClient.get("/auth/me");
      setUser(me.data);
      navigate("/");
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? "Error al iniciar sesión";
      if (typeof detail === "string" && detail.toLowerCase().includes("mfa")) {
        setNeedsMfa(true);
      }
      setServerError(detail);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-12 bg-white rounded-xl border border-slate-200 p-8">
      <h1 className="font-display text-2xl font-bold mb-6">Iniciar sesión</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="text-sm font-medium text-slate-700">Correo electrónico</label>
          <input
            type="email"
            {...register("email")}
            className="mt-1 w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
          />
          {errors.email && <p className="text-red-600 text-xs mt-1">{errors.email.message}</p>}
        </div>
        <div>
          <label className="text-sm font-medium text-slate-700">Contraseña</label>
          <input
            type="password"
            {...register("password")}
            className="mt-1 w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
          />
          {errors.password && <p className="text-red-600 text-xs mt-1">{errors.password.message}</p>}
        </div>
        {needsMfa && (
          <div>
            <label className="text-sm font-medium text-slate-700">Código MFA (TOTP)</label>
            <input
              type="text"
              {...register("mfa_code")}
              className="mt-1 w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
              placeholder="123456"
            />
          </div>
        )}
        {serverError && <p className="text-red-600 text-sm">{serverError}</p>}
        <button
          type="submit"
          className="w-full bg-ink text-white rounded-md py-2.5 font-medium hover:bg-brand-700 transition-colors"
        >
          Ingresar
        </button>
      </form>
    </div>
  );
}
