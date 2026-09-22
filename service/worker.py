import asyncio
import base64
import json
import logging
import os
from datetime import datetime, timezone

import aio_pika
from aio_pika import Message, DeliveryMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://guest:guest@localhost:5672/"
)

INPUT_QUEUE = os.getenv("RABBITMQ_INPUT_QUEUE", "wine_scan_tasks")
RESULT_QUEUE = os.getenv("RABBITMQ_RESULT_QUEUE", "wine_scan_results")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def publish_result(channel, result: dict) -> None:
    message = Message(
        body=json.dumps(
            result,
            ensure_ascii=False
        ).encode("utf-8"),
        content_type="application/json",
        delivery_mode=DeliveryMode.PERSISTENT,
    )

    await channel.default_exchange.publish(
        message,
        routing_key=RESULT_QUEUE,
    )


async def process_wine_task(
    message: aio_pika.abc.AbstractIncomingMessage,
    channel,
) -> None:
    try:
        data = json.loads(message.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.error("Некорректное входное сообщение: %s", exc)
        await message.reject(requeue=False)
        return

    # Поддерживаем оба варианта регистра:
    # camelCase — будущий контракт,
    # PascalCase — текущая сериализация C#.
    task_id = data.get("taskId") or data.get("TaskId")

    if not task_id:
        logger.error("В сообщении отсутствует taskId")
        await message.reject(requeue=False)
        return

    image_base64 = data.get("imageBase64") or data.get("ImageBase64")

    if not image_base64:
        result = {
            "schemaVersion": 1,
            "taskId": task_id,
            "status": "Failed",
            "result": None,
            "alternatives": [],
            "error": "Поле imageBase64 отсутствует",
            "createdAtUtc": utc_now(),
        }

        try:
            await publish_result(channel, result)
            await message.ack()
        except Exception:
            logger.exception(
                "Не удалось опубликовать ошибку для задачи %s",
                task_id,
            )
            await message.nack(requeue=True)

        return

    try:
        base64.b64decode(image_base64, validate=True)
    except (ValueError, TypeError):
        result = {
            "schemaVersion": 1,
            "taskId": task_id,
            "status": "Failed",
            "result": None,
            "alternatives": [],
            "error": "Некорректное Base64-изображение",
            "createdAtUtc": utc_now(),
        }

        try:
            await publish_result(channel, result)
            await message.ack()
        except Exception:
            logger.exception(
                "Не удалось опубликовать ошибку для задачи %s",
                task_id,
            )
            await message.nack(requeue=True)

        return

    logger.info("Получена задача %s", task_id)

    try:
        # Временная заглушка до подключения SigLIP/OCR/VLM.
        await asyncio.sleep(2)

        result = {
            "schemaVersion": 1,
            "taskId": task_id,
            "status": "Completed",
            "result": {
                "slug": "test-wine-slug",
                "name": "Тестовое российское вино",
                "rating": 87,
                "year": 2022,
                "country": "Россия",
                "region": "Краснодарский край",
                "fact": "Тестовый результат ML-сервиса",
                "confidence": 0.5,
                "top1Score": 0.5,
                "top5Score": 0.5,
            },
            "alternatives": [],
            "error": None,
            "createdAtUtc": utc_now(),
        }

        await publish_result(channel, result)
        await message.ack()

        logger.info(
            "Результат задачи %s опубликован в %s",
            task_id,
            RESULT_QUEUE,
        )
    except Exception:
        logger.exception(
            "Ошибка обработки задачи %s; сообщение возвращается в очередь",
            task_id,
        )
        await message.nack(requeue=True)


async def main() -> None:
    connection = await aio_pika.connect_robust(RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)

        input_queue = await channel.declare_queue(
        INPUT_QUEUE,
        durable=True,
        )

        await channel.declare_queue(
            RESULT_QUEUE,
            durable=True,
        )

        async def handler(message):
            await process_wine_task(message, channel)

        await input_queue.consume(handler)

        logger.info(
            "ML worker слушает очередь %s",
            INPUT_QUEUE,
        )

        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("ML worker остановлен")