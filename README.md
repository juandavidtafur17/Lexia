# ERP Marketplace Core v2.1

Plataforma **ERP Comercial + Marketplace** de alta concurrencia. Backend
asíncrono en FastAPI + SQLAlchemy 2.0 sobre PostgreSQL, caché/colas en
Redis, búsqueda en Elasticsearch, pagos reales vía Stripe, y frontend en
React 18 + TypeScript + Vite.

> **Estado de esta entrega**: este repositorio contiene código de backend y
> frontend real y funcional para los flujos núcleo (auth, catálogo,
> inventario, carrito, checkout transaccional, pagos, reportes, WebSockets,
> tareas asíncronas). **No es una maqueta ni usa datos simulados** — cada
> endpoint ejecuta lógica de negocio real contra una base de datos real.
> Antes de operar en producción, complete las credenciales reales indicadas
> más abajo (Stripe, SMTP, S3) y ejecute sus propias pruebas de carga.

---

## 1. Arquitectura

```
CAPA PRESENTACIÓN    → Vite + React 18 + TypeScript + Tailwind + Zustand + TanStack Query
CAPA SERVICIOS/API   → FastAPI async + Celery (workers + beat) + JWT RS256 + WebSockets
CAPA PERSISTENCIA    → PostgreSQL 16 (SQLAlchemy 2.0 async) + Redis 7 + Elasticsearch 8 + S3/MinIO
```

Ver el árbol completo de directorios en la raíz del repositorio; cada
carpeta (`backend/`, `frontend/`, `database/`, `nginx/`, `deployment/`,
`scripts/`, `tests/`) corresponde exactamente a la especificación de
arquitectura entregada.

---

## 2. Requisitos previos

- Docker y Docker Compose v2
- (Para desarrollo sin Docker) Python 3.12+, Node.js 20+, PostgreSQL 16, Redis 7

---

## 3. Puesta en marcha (Docker — recomendado)

```bash
cp .env.example .env
# Edite .env: contraseñas de Postgres, SECRET_KEY, credenciales de Stripe/SMTP/S3

./scripts/generate_jwt_keys.sh backend/keys   # genera el par RS256 para firmar JWT

docker compose up --build -d

# Cree el esquema de base de datos y datos base (almacén, impuestos, permisos)
docker compose exec backend python scripts/init_db.py
```

Servicios expuestos:
| Servicio    | URL                              |
|-------------|-----------------------------------|
| Frontend    | http://localhost:5173 (o :80 vía Nginx) |
| API         | http://localhost:8000/api/v1      |
| Docs OpenAPI| http://localhost:8000/api/docs    |
| MinIO Console | http://localhost:9001           |

---

## 4. Migraciones de base de datos (Alembic)

`scripts/init_db.py` crea el esquema inicial. Para **cambios posteriores**
use Alembic (nunca edite tablas a mano en producción):

```bash
cd database
alembic revision --autogenerate -m "descripcion del cambio"
alembic upgrade head
```

---

## 5. Credenciales externas reales requeridas

Estas integraciones están implementadas con SDKs reales, pero requieren que
usted provea sus propias credenciales — no se incluyen llaves de terceros:

| Servicio        | Variable(s) en `.env`                          | Dónde obtenerlas |
|------------------|------------------------------------------------|-------------------|
| Stripe (pagos)   | `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`       | Dashboard de Stripe → Developers → API keys |
| SMTP (correo)    | `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`       | Su proveedor de correo transaccional (SES, SendGrid, Postmark, etc.) |
| S3/MinIO (archivos) | `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`| MinIO local (incluido en docker-compose) o AWS S3 en producción |

Sin estas credenciales, los endpoints correspondientes (pago, envío de
correo, subida de facturas) responderán con errores explícitos indicando
qué falta — no fallan en silencio ni simulan una respuesta exitosa.

---

## 6. Pruebas

```bash
cd backend
pip install -r requirements.txt --break-system-packages
export TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/erp_test
pytest ../tests -v
```

`tests/test_orders_flow.py` valida el flujo crítico de negocio: que el
checkout reserva stock de forma atómica y que la sobreventa concurrente es
imposible (usa `SELECT ... FOR UPDATE` a nivel de fila).

---

## 7. Decisiones de diseño relevantes

- **Alta de vendedor instantánea**: `POST /api/v1/sellers/apply` aprueba al
  vendedor de inmediato (modelo de autoservicio tipo Amazon Seller Central /
  Facebook Marketplace) y sus productos se publican con `status=ACTIVE` desde
  la creación — visibles en el catálogo al instante. La moderación ocurre
  post-publicación (reportes, revisión de catálogo), no como bloqueo previo.
  Si su negocio requiere aprobación manual antes de publicar, cambie
  `is_approved=True` por `False` en `sellers.py` y reactive el estado
  `PENDING_REVIEW` en `products.py`.
- **Nunca se confía en el precio enviado por el cliente**: todo precio se
  recalcula server-side desde `ProductVariant.price` al crear el pedido.
- **Reserva antes que descuento físico**: al pagar se reserva
  `quantity_reserved`; el descuento de `quantity_on_hand` ocurre al
  despachar, permitiendo cancelar sin perder trazabilidad.
- **Reservas expiran automáticamente** (tarea Celery periódica) si el pago
  no se completa en `ORDER_RESERVATION_MINUTES`.
- **JWT asimétrico (RS256)**: la llave privada nunca sale del backend; solo
  la pública sería necesaria si en el futuro otro servicio necesita
  verificar tokens de forma independiente.
- **No se almacenan datos de tarjeta**: Stripe Elements tokeniza en el
  cliente; el backend solo maneja `PaymentIntent` y webhooks firmados.

---

## 8. Próximos pasos sugeridos para producción

Esta base cubre los flujos núcleo con código real. Para un despliegue de
producción a escala "Amazon-like" descrito en la especificación original,
los siguientes puntos requieren trabajo adicional de su equipo (no son
simulables sin su infraestructura real):

- Clúster de Elasticsearch multi-nodo con réplicas (aquí se configura un
  nodo único de desarrollo).
- Migración de Docker Compose a Kubernetes (manifiestos en `deployment/`
  quedan como siguiente iteración).
- Certificados TLS/SSL en Nginx (`deployment/` — actualmente HTTP en
  desarrollo).
- Motor de recomendaciones por embeddings vectoriales e IA generativa para
  resúmenes de reseñas (el modelo de datos ya contempla
  `ai_sentiment_summary` en `Review`, listo para integrarse).
- Panel de Business Intelligence consolidado (`analytics/` en el frontend
  está mapeado pero no implementado en esta entrega).
