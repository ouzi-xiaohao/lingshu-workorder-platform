import json

from src.core.config import settings


class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        try:
            import aio_pika
            self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            self.channel = await self.connection.channel(publisher_confirms=True)
            await self.channel.set_qos(prefetch_count=16)
        except Exception:
            self.connection = self.channel = None
        return self.channel

    async def publish(self, routing_key: str, payload: dict):
        if not self.channel and not await self.connect():
            return False
        import aio_pika
        exchange = self.channel.default_exchange
        await exchange.publish(aio_pika.Message(body=json.dumps(payload, ensure_ascii=False).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key=routing_key)
        return True

    async def close(self):
        if self.connection:
            await self.connection.close()


rabbitmq_client = RabbitMQClient()
