"""
Gestor de conexiones WebSocket para actualizaciones en tiempo real:
tabla de inventario del ERP, panel de subastas/ofertas del Marketplace y
notificaciones push in-app. Usa un registro en memoria por proceso; en
despliegue multi-réplica las actualizaciones se propagan vía Redis Pub/Sub
(canal "ws_broadcast") para que todas las instancias de backend las repliquen.
"""
import json
import uuid

import redis.asyncio as aioredis
from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import settings


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}
        self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def connect(self, channel: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.setdefault(channel, []).append(websocket)

    def disconnect(self, channel: str, websocket: WebSocket) -> None:
        conns = self.active_connections.get(channel, [])
        if websocket in conns:
            conns.remove(websocket)

    async def broadcast_local(self, channel: str, message: dict) -> None:
        dead = []
        for ws in self.active_connections.get(channel, []):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(channel, ws)

    async def publish(self, channel: str, message: dict) -> None:
        """Publica en Redis para que TODAS las réplicas de backend retransmitan a sus clientes locales."""
        await self._redis.publish(f"ws:{channel}", json.dumps(message))
        await self.broadcast_local(channel, message)

    async def subscribe_and_relay(self, channel: str) -> None:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(f"ws:{channel}")
        async for message in pubsub.listen():
            if message["type"] == "message":
                await self.broadcast_local(channel, json.loads(message["data"]))


manager = ConnectionManager()


async def inventory_ws_endpoint(websocket: WebSocket, warehouse_id: str) -> None:
    channel = f"inventory:{warehouse_id}"
    await manager.connect(channel, websocket)
    try:
        while True:
            # El cliente puede enviar pings; el servidor empuja updates vía manager.publish()
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(channel, websocket)


async def notifications_ws_endpoint(websocket: WebSocket, user_id: uuid.UUID) -> None:
    channel = f"notifications:{user_id}"
    await manager.connect(channel, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(channel, websocket)
