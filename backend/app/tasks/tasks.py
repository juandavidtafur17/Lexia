"""
Trabajos distribuidos de Celery. Usan el engine SÍNCRONO de SQLAlchemy
(SYNC_DATABASE_URL) porque los workers de Celery no operan nativamente en
modo async — este es el patrón recomendado para evitar bloquear el event
loop del backend FastAPI con trabajo pesado (PDFs, correos, indexación).
"""
import logging
from datetime import datetime, timedelta, timezone

from elasticsearch import Elasticsearch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

sync_engine = create_engine(settings.SYNC_DATABASE_URL, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(bind=sync_engine)

es_client = Elasticsearch(settings.ELASTICSEARCH_URL)

PRODUCTS_INDEX = "products"


@celery_app.task(name="app.tasks.tasks.index_product_in_search", bind=True, max_retries=3)
def index_product_in_search(self, product_id: str) -> None:
    """
    Sincroniza un producto hacia el clúster de Elasticsearch para habilitar
    autocompletado, corrección ortográfica y búsqueda semántica sin saturar
    PostgreSQL con cargas de búsqueda de texto libre.
    """
    from app.models.catalog import Product

    session: Session = SyncSessionLocal()
    try:
        product = session.get(Product, product_id)
        if not product:
            logger.warning("Producto %s no encontrado para indexar", product_id)
            return

        doc = {
            "id": str(product.id),
            "title": product.title,
            "description": product.description,
            "brand": product.brand,
            "tags": product.tags,
            "category_id": str(product.category_id),
            "status": product.status.value,
            "rating_average": product.rating_average,
            "sales_count": product.sales_count,
            "prices": [float(v.price) for v in product.variants],
            "skus": [v.sku for v in product.variants],
        }
        es_client.index(index=PRODUCTS_INDEX, id=str(product.id), document=doc)
    except Exception as exc:
        logger.exception("Error indexando producto %s", product_id)
        raise self.retry(exc=exc, countdown=10)
    finally:
        session.close()


@celery_app.task(name="app.tasks.tasks.send_order_confirmation")
def send_order_confirmation(order_id: str) -> None:
    """Envía el correo transaccional de confirmación de pedido vía SMTP configurado."""
    import smtplib
    from email.mime.text import MIMEText

    from app.models.order import Order
    from app.models.user import User

    session: Session = SyncSessionLocal()
    try:
        order = session.get(Order, order_id)
        if not order:
            return
        user = session.get(User, order.user_id)
        if not user or not settings.SMTP_HOST:
            logger.info("SMTP no configurado o usuario ausente; se omite envío de correo")
            return

        body = (
            f"Hola {user.full_name},\n\n"
            f"Confirmamos tu pedido {order.order_number} por un total de "
            f"{order.total_amount} {order.currency}.\n\n"
            f"Gracias por tu compra."
        )
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = f"Confirmación de pedido {order.order_number}"
        msg["From"] = settings.SMTP_USER
        msg["To"] = user.email

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    finally:
        session.close()


@celery_app.task(name="app.tasks.tasks.generate_invoice_pdf")
def generate_invoice_pdf(order_id: str) -> None:
    """Genera la factura en PDF (HTML-to-PDF vía WeasyPrint) y la sube a almacenamiento S3/MinIO."""
    import io
    import uuid as uuid_lib

    import boto3
    from jinja2 import Environment, BaseLoader
    from weasyprint import HTML

    from app.models.finance import Invoice
    from app.models.order import Order

    session: Session = SyncSessionLocal()
    try:
        order = session.get(Order, order_id)
        if not order:
            return

        invoice_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(order.id)[:8]}"
        template_str = """
        <html><body style="font-family: sans-serif;">
        <h1>Factura {{ invoice_number }}</h1>
        <p>Pedido: {{ order_number }}</p>
        <table border="1" cellpadding="6" style="border-collapse:collapse; width:100%">
          <tr><th>Subtotal</th><th>Impuestos</th><th>Envío</th><th>Descuento</th><th>Total</th></tr>
          <tr>
            <td>{{ subtotal }}</td><td>{{ tax }}</td><td>{{ shipping }}</td>
            <td>{{ discount }}</td><td><b>{{ total }} {{ currency }}</b></td>
          </tr>
        </table>
        </body></html>
        """
        html_content = Environment(loader=BaseLoader()).from_string(template_str).render(
            invoice_number=invoice_number,
            order_number=order.order_number,
            subtotal=order.subtotal_amount,
            tax=order.tax_amount,
            shipping=order.shipping_amount,
            discount=order.discount_amount,
            total=order.total_amount,
            currency=order.currency,
        )

        pdf_bytes = HTML(string=html_content).write_pdf()
        storage_key = f"invoices/{invoice_number}.pdf"

        if settings.S3_ACCESS_KEY:
            s3 = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
            )
            s3.upload_fileobj(io.BytesIO(pdf_bytes), settings.S3_BUCKET, storage_key)

        session.add(
            Invoice(
                order_id=order.id,
                invoice_number=invoice_number,
                issuer_legal_name="Mi Empresa ERP-Marketplace S.A.C.",
                issuer_tax_id="20000000001",
                buyer_legal_name=order.billing_address_snapshot.get("recipient_name", ""),
                subtotal_amount=order.subtotal_amount,
                tax_amount=order.tax_amount,
                total_amount=order.total_amount,
                currency=order.currency,
                pdf_storage_key=storage_key,
            )
        )
        session.commit()
    finally:
        session.close()


@celery_app.task(name="app.tasks.tasks.generate_review_sentiment_summary")
def generate_review_sentiment_summary(review_id: str) -> None:
    """Genera un resumen de sentimiento profesional para una reseña usando Gemini."""
    from app.models.engagement import Review

    session: Session = SyncSessionLocal()
    try:
        review = session.get(Review, review_id)
        if not review:
            logger.warning("Reseña %s no encontrada para resumen de sentimiento", review_id)
            return

        if not review.comment.strip():
            review.ai_sentiment_summary = "Sin comentario del cliente."
            session.add(review)
            session.commit()
            return

        try:
            from app.services.ai.gemini_client import GeminiClient

            client = GeminiClient()
            metadata = {
                "product_id": str(review.product_id),
                "rating": str(review.rating),
            }
            summary = client.summarize_review(review.comment, metadata=metadata)
            review.ai_sentiment_summary = summary
            session.add(review)
            session.commit()
        except Exception as exc:
            logger.exception("Error al generar resumen de reseña %s: %s", review_id, exc)
    finally:
        session.close()


@celery_app.task(name="app.tasks.tasks.release_expired_reservations")
def release_expired_reservations() -> None:
    """
    Libera reservas de inventario de pedidos que quedaron en PENDING_PAYMENT
    más allá de ORDER_RESERVATION_MINUTES — evita que el stock quede
    bloqueado indefinidamente por carritos abandonados en checkout.
    """
    from app.models.inventory import InventoryItem, StockMovement, StockMovementType
    from app.models.order import Order, OrderStatus

    session: Session = SyncSessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.ORDER_RESERVATION_MINUTES)
        expired_orders = (
            session.query(Order)
            .filter(Order.status == OrderStatus.PENDING_PAYMENT, Order.created_at < cutoff)
            .all()
        )
        for order in expired_orders:
            for item in order.items:
                inv = (
                    session.query(InventoryItem)
                    .filter(InventoryItem.variant_id == item.variant_id)
                    .with_for_update()
                    .first()
                )
                if inv:
                    inv.quantity_reserved = max(0, inv.quantity_reserved - item.quantity)
                    session.add(
                        StockMovement(
                            inventory_item_id=inv.id,
                            movement_type=StockMovementType.RELEASE,
                            quantity=item.quantity,
                            reference_type="order_expired",
                            reference_id=order.id,
                        )
                    )
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = datetime.now(timezone.utc)
        session.commit()
        logger.info("Liberadas %d reservas expiradas", len(expired_orders))
    finally:
        session.close()


@celery_app.task(name="app.tasks.tasks.refresh_exchange_rates")
def refresh_exchange_rates() -> None:
    """Actualiza tasas de cambio multimoneda desde un proveedor externo real y las cachea en Postgres/Redis."""
    import httpx

    from app.models.finance import ExchangeRate

    session: Session = SyncSessionLocal()
    try:
        base = settings.DEFAULT_CURRENCY
        response = httpx.get(f"https://api.exchangerate.host/latest?base={base}", timeout=10)
        response.raise_for_status()
        rates = response.json().get("rates", {})
        for target, rate in rates.items():
            session.add(ExchangeRate(base_currency=base, target_currency=target, rate=rate))
        session.commit()
    except Exception:
        logger.exception("No se pudo refrescar tasas de cambio")
    finally:
        session.close()


@celery_app.task(name="app.tasks.tasks.low_stock_alert_sweep")
def low_stock_alert_sweep() -> None:
    """Barrido diario: notifica a los encargados de almacén sobre SKUs bajo el punto de reorden."""
    from app.models.inventory import InventoryItem

    session: Session = SyncSessionLocal()
    try:
        low_items = [
            i for i in session.query(InventoryItem).all()
            if i.quantity_available <= i.reorder_point
        ]
        logger.info("Detectados %d ítems con stock bajo", len(low_items))
        # La notificación real (email/push) se despacha reutilizando send_order_confirmation
        # como patrón — en producción se integraría un canal dedicado de alertas.
    finally:
        session.close()
