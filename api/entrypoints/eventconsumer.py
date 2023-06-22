import asyncio
import json
import logging
import redis.asyncio as redis
from api import bootstrap, config
from api.domain import events, commands
from api.adapters.notifications import EmailLocalNotifications

logger = logging.getLogger(__name__)

r = redis.Redis(**config.get_redis_host_and_port())


async def main():
    logger.info("Redis pubsub starting")
    bus = bootstrap.bootstrap(notifications=EmailLocalNotifications())
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe("products")

    async for m in pubsub.listen():
        await pong(m, bus)


async def pong(m, bus):
    logger.info("handling %s", m)
    try:
        event = json.loads(m["data"])
        if event["event"] == "ProductDiscount":
            print("Sending notification..")
            cmd = commands.NotifyOrderSale()
            result = await bus.handle(cmd)
            print(result)
    except Exception as e:
        logger.error(e)
        logger.error(e)

        pass


if __name__ == "__main__":
    asyncio.run(main())
