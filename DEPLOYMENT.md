# Despliegue completo

Este repositorio contiene:

- `backend/` — FastAPI asíncrono con PostgreSQL, Redis, Elasticsearch, Celery y S3/MinIO.
- `frontend/` — React + Vite + TypeScript.

## Frontend en Vercel

Ya se agregó `vercel.json` en la raíz para desplegar solo el frontend.
Tu proyecto está configurado como aplicación estática con build de Vite.

### Configuración de Vercel

- `Root Directory`: raíz del repo
- `Install Command`: `npm install`
- `Build Command`: `npm run build`
- `Output Directory`: `frontend/dist`

### Variables de entorno necesarias en Vercel

- `VITE_API_URL` — URL base del backend (por ejemplo, `https://api.tudominio.com`)
- `VITE_STRIPE_PUBLIC_KEY` — clave pública de Stripe para el checkout

Si esta variable está definida, el frontend usará:

- `VITE_API_URL/api/v1`

Si no está definida, utilizará la ruta relativa `/api/v1`.

## Backend completo

El backend no puede desplegarse como una sola función estática en Vercel.
Este backend requiere:

- PostgreSQL
- Redis
- Elasticsearch
- Celery workers
- S3/MinIO o servicio compatible
- Stripe y SMTP para pagos y notificaciones

### La forma recomendada

Usa Docker Compose para ejecutarlo completo local o en un servidor con Docker:

```bash
cp .env.example .env
# Edita .env con tus credenciales reales y rutas de servicio

docker compose up --build -d
```

Luego inicia la base de datos y los datos base:

```bash
docker compose exec backend python scripts/init_db.py
```

## Flujo completo ideal

1. Despliega el backend en un host que soporte Docker o contenedores.
2. Configura los servicios externos (PostgreSQL, Redis, Elasticsearch, S3, Stripe).
3. Despliega el frontend en Vercel usando `vercel.json`.
4. En Vercel, define `VITE_API_URL` apuntando a tu backend.

## Nota final

- `frontend` está listo para Vercel.
- `backend` está listo para Docker Compose o un servicio de contenedores.
- No es posible desplegar el backend completo de este stack directamente como un único sitio Vercel sin infraestructura externa.
