import asyncio
import json
import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import aio_pika

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ViniFind RABBITMQ Microservice", version="1.0.0")

# Настройки RabbitMQ (в Docker Compose хост будет называться 'rabbitmq')
RABBITMQ_URL = "amqp://guest:guest@localhost/"

# Pydantic-модель для входящего запроса
class WineTaskRequest(BaseModel):
    label_id: str
    image_url: str

async def send_to_rabbitmq(message_body: dict):
    """
    Отправляет задачу в очередь RabbitMQ
    """
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            # Объявляем очередь
            queue = await channel.declare_queue("wine_tasks", durable=True)
            
            # Публикуем сообщение
            message = aio_pika.Message(
                body=json.dumps(message_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            await channel.default_exchange.publish(
                message,
                routing_key="wine_tasks"
            )
            logger.info(f"📤 Задача {message_body.get('label_id')} отправлена в RabbitMQ")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к RabbitMQ: {e}")
        raise HTTPException(status_code=500, detail="RabbitMQ connection error")

@app.post("/api/v1/recognize")
async def recognize_wine(task: WineTaskRequest, background_tasks: BackgroundTasks):
    """
    Эндпоинт для приема запроса на распознавание вина
    """
    task_data = {
        "label_id": task.label_id,
        "image_url": task.image_url
    }
    
    # Отправляем в очередь асинхронно через фоновые задачи FastAPI
    background_tasks.add_task(send_to_origin_queue, task_data)
    
    return {
        "status": "accepted",
        "message": "Задача принята в обработку",
        "label_id": task.label_id
    }

async def send_to_origin_queue(data: dict):
    await send_to_rabbitmq(data)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ml-microservice"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)