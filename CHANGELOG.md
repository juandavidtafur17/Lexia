# Changelog

## [2.1.0] - Núcleo funcional inicial
### Añadido
- Autenticación JWT (RS256) con refresh tokens, MFA (TOTP) y bloqueo anti fuerza bruta vía Redis.
- Catálogo: categorías, productos y variantes (SKU) con atributos dinámicos.
- Inventario multizona/multialmacén con bitácora de movimientos y ajustes atómicos (`SELECT ... FOR UPDATE`).
- Carrito persistente y checkout transaccional con reserva de stock (previene sobreventa bajo concurrencia).
- Integración de pagos con Stripe (PaymentIntent + verificación de firma de webhook).
- Motor de reportes: Excel (openpyxl) y PDF (reportlab/WeasyPrint) generados a partir de datos reales.
- Tareas asíncronas con Celery: indexación en Elasticsearch, envío de correos, generación de facturas, liberación de reservas expiradas, actualización de tasas de cambio.
- WebSockets para inventario en tiempo real y notificaciones in-app.
- Frontend React + TypeScript + Vite con TanStack Query, Zustand, React Hook Form + Zod, y Stripe Elements.
- Orquestación completa vía Docker Compose (Postgres, Redis, Elasticsearch, MinIO, Nginx).
